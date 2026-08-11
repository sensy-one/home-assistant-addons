from flask import Flask, jsonify, request, Response, send_from_directory
import copy
import json
import logging
import os
import re
import sys

import requests

app = Flask(__name__)

SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = os.getenv('HA_URL')
HA_TOKEN = os.getenv('HA_TOKEN')
FLOORPLAN_STORE = os.getenv('FLOORPLAN_STORE', '/data/zone_editor_floorplans.json')
TARGET_COORDINATE_RE = re.compile(r'target_(\d+)_(x|y)$', re.IGNORECASE)

RADAR_DISCOVERY_TEMPLATE = r"""
{% set out = namespace(items=[], ids=[]) %}
{% for s in states %}
  {% set dev = s.entity_id | device_id %}
  {% if dev and (device_attr(dev, 'manufacturer') or '') == 'Sensy-One' and dev not in out.ids %}
    {% set identifiers = namespace(items=[]) %}
    {% for pair in (device_attr(dev, 'identifiers') or []) %}
      {% set identifiers.items = identifiers.items + [[pair[0] | string, pair[1] | string]] %}
    {% endfor %}
    {% set connections = namespace(items=[]) %}
    {% for pair in (device_attr(dev, 'connections') or []) %}
      {% set connections.items = connections.items + [[pair[0] | string, pair[1] | string]] %}
    {% endfor %}
    {% set out.items = out.items + [{
      'device_id': dev,
      'name': device_attr(dev, 'name_by_user') or device_attr(dev, 'name') or dev,
      'model': device_attr(dev, 'model') or '',
      'manufacturer': device_attr(dev, 'manufacturer') or '',
      'serial_number': device_attr(dev, 'serial_number') or '',
      'composite_device_id': device_attr(dev, 'composite_device_id') or '',
      'identifiers': identifiers.items,
      'connections': connections.items,
      'entity_ids': device_entities(dev)
    }] %}
    {% set out.ids = out.ids + [dev] %}
  {% endif %}
{% endfor %}
{{ out.items | tojson }}
""".strip()

if SUPERVISOR_TOKEN:
    HOME_ASSISTANT_API = 'http://supervisor/core/api'
    headers = {'Authorization': f'Bearer {SUPERVISOR_TOKEN}', 'Content-Type': 'application/json'}
elif HA_URL and HA_TOKEN:
    HOME_ASSISTANT_API = HA_URL.rstrip('/') + '/api'
    headers = {'Authorization': f'Bearer {HA_TOKEN}', 'Content-Type': 'application/json'}
else:
    logging.error('No SUPERVISOR_TOKEN found and no HA_URL/HA_TOKEN.')
    sys.exit(1)

def ha_post(path, json=None, timeout=20):
    return requests.post(f'{HOME_ASSISTANT_API}{path}', headers=headers, json=json, timeout=timeout)


def _normalize_pair_list(value, *, connections=False):
    """Return stable, JSON-safe registry identifier/connection pairs."""
    pairs = set()
    for pair in value or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        kind = str(pair[0]).strip().casefold()
        item = str(pair[1]).strip().casefold()
        if not kind or not item:
            continue
        if connections and kind == 'mac':
            item = re.sub(r'[^0-9a-f]', '', item)
        pairs.add((kind, item))
    return [list(pair) for pair in sorted(pairs)]


def _target_coordinate_entities(entity_ids):
    """Return coordinates only for targets that expose both an X and a Y entity."""
    by_target = {}
    for raw_entity_id in entity_ids or []:
        entity_id = str(raw_entity_id).strip()
        match = TARGET_COORDINATE_RE.search(entity_id)
        if not match:
            continue
        by_target.setdefault(match.group(1), {})[match.group(2).casefold()] = entity_id

    complete = []
    for axes in by_target.values():
        if 'x' in axes and 'y' in axes:
            complete.extend((axes['x'], axes['y']))
    return sorted(set(complete), key=str.casefold)


def filter_radar_devices(rows):
    """Build usable Sensy-One radar references from Home Assistant device rows."""
    devices = []
    seen_device_ids = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        device_id = str(row.get('device_id') or '').strip()
        manufacturer = str(row.get('manufacturer') or '').strip()
        target_entities = _target_coordinate_entities(row.get('entity_ids'))
        if (
            not device_id
            or device_id in seen_device_ids
            or manufacturer.casefold() != 'sensy-one'
            or not target_entities
        ):
            continue

        identity = {
            'identifiers': _normalize_pair_list(row.get('identifiers')),
            'connections': _normalize_pair_list(
                row.get('connections'), connections=True
            ),
            'serial_number': str(row.get('serial_number') or '').strip(),
            'target_entities': target_entities,
        }
        devices.append({
            'device_id': device_id,
            'name': str(row.get('name') or device_id),
            'model': str(row.get('model') or ''),
            'composite_device_id': str(
                row.get('composite_device_id') or ''
            ).strip(),
            'radar_identity': identity,
        })
        seen_device_ids.add(device_id)
    return devices


def discover_radar_devices():
    """Query HA once and apply the shared usable-radar definition."""
    response = ha_post('/template', {'template': RADAR_DISCOVERY_TEMPLATE})
    if response.status_code != 200:
        raise RuntimeError(f'Home Assistant template error: {response.text}')
    try:
        rows = response.json() or []
    except ValueError as err:
        raise RuntimeError('Home Assistant returned invalid radar discovery JSON') from err
    if not isinstance(rows, list):
        raise RuntimeError('Home Assistant returned an invalid radar discovery result')
    return filter_radar_devices(rows)


def _identity_pair_set(identity, key, *, connections=False):
    return {
        tuple(pair)
        for pair in _normalize_pair_list(
            (identity or {}).get(key), connections=connections
        )
    }


def _identity_matches(reference_identity, device_identity):
    """Return true when any durable physical identity signal agrees."""
    reference_identifiers = _identity_pair_set(reference_identity, 'identifiers')
    device_identifiers = _identity_pair_set(device_identity, 'identifiers')
    if reference_identifiers & device_identifiers:
        return True

    reference_connections = _identity_pair_set(
        reference_identity, 'connections', connections=True
    )
    device_connections = _identity_pair_set(
        device_identity, 'connections', connections=True
    )
    if reference_connections & device_connections:
        return True

    reference_serial = str(
        (reference_identity or {}).get('serial_number') or ''
    ).strip().casefold()
    device_serial = str(
        (device_identity or {}).get('serial_number') or ''
    ).strip().casefold()
    if reference_serial and reference_serial == device_serial:
        return True

    reference_entities = {
        str(entity_id).strip().casefold()
        for entity_id in (reference_identity or {}).get('target_entities', [])
        if str(entity_id).strip()
    }
    device_entities = {
        str(entity_id).strip().casefold()
        for entity_id in (device_identity or {}).get('target_entities', [])
        if str(entity_id).strip()
    }
    return bool(reference_entities & device_entities)


def _legacy_reference_matches(reference, device):
    """Match old name/model metadata only when all available values agree."""
    reference_name = str(reference.get('name') or '').strip().casefold()
    if not reference_name:
        return False
    if reference_name != str(device.get('name') or '').strip().casefold():
        return False
    reference_model = str(reference.get('model') or '').strip().casefold()
    if reference_model:
        return reference_model == str(device.get('model') or '').strip().casefold()
    return True


def _enrich_radar_reference(reference, device):
    enriched = copy.deepcopy(reference)
    enriched['device_id'] = device['device_id']
    if 'deviceId' in enriched:
        enriched['deviceId'] = device['device_id']
    enriched['name'] = device.get('name') or device['device_id']
    enriched['model'] = device.get('model') or ''
    enriched['radar_identity'] = copy.deepcopy(device.get('radar_identity') or {})
    return enriched


def resolve_radar_reference(reference, devices):
    """Resolve one stored reference without ever choosing an ambiguous device."""
    if not isinstance(reference, dict):
        return reference, False, 'Radar reference is not an object and was preserved'

    stored_device_id = str(
        reference.get('device_id') or reference.get('deviceId') or ''
    ).strip()
    exact = [device for device in devices if device['device_id'] == stored_device_id]
    if len(exact) == 1:
        enriched = _enrich_radar_reference(reference, exact[0])
        return enriched, enriched != reference, None

    composite = [
        device for device in devices
        if stored_device_id
        and device.get('composite_device_id') == stored_device_id
    ]
    if len(composite) == 1:
        enriched = _enrich_radar_reference(reference, composite[0])
        return enriched, enriched != reference, None
    if len(composite) > 1:
        return (
            reference,
            False,
            f'Radar reference {stored_device_id!r} matches multiple 2026.8 splits',
        )

    reference_identity = reference.get('radar_identity')
    if isinstance(reference_identity, dict) and reference_identity:
        stable = [
            device for device in devices
            if _identity_matches(
                reference_identity, device.get('radar_identity') or {}
            )
        ]
        if len(stable) == 1:
            enriched = _enrich_radar_reference(reference, stable[0])
            return enriched, enriched != reference, None
        if len(stable) > 1:
            return (
                reference,
                False,
                f'Radar reference {stored_device_id!r} has ambiguous stable identity',
            )
        return (
            reference,
            False,
            f'Radar reference {stored_device_id!r} has no current stable-identity match',
        )

    legacy = [
        device for device in devices
        if _legacy_reference_matches(reference, device)
    ]
    if len(legacy) == 1:
        enriched = _enrich_radar_reference(reference, legacy[0])
        return enriched, enriched != reference, None
    if len(legacy) > 1:
        return (
            reference,
            False,
            f'Legacy radar reference {stored_device_id!r} is ambiguous; placement preserved',
        )
    return (
        reference,
        False,
        f'No valid radar matches legacy reference {stored_device_id!r}; placement preserved',
    )


def resolve_radar_references(references, devices, label='sensor'):
    resolved = []
    changed = False
    warnings = []
    for index, reference in enumerate(references or []):
        next_reference, reference_changed, warning = resolve_radar_reference(
            reference, devices
        )
        resolved.append(next_reference)
        changed = changed or reference_changed
        if warning:
            warnings.append(f'{label} {index + 1}: {warning}')
    return resolved, changed, warnings

def floorplan_entity_id(floor_id: str) -> str:
    safe = re.sub(r'[^a-z0-9_]+', '_', floor_id.lower())
    safe = re.sub(r'_+', '_', safe).strip('_')
    if not safe:
        safe = 'floor'
    return f'zone_editor_floorplan.{safe}'

def load_store():
    try:
        with open(FLOORPLAN_STORE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.warning('Failed to read floorplan store: %s', e)
        return {}

def save_store(data):
    try:
        os.makedirs(os.path.dirname(FLOORPLAN_STORE), exist_ok=True)
        with open(FLOORPLAN_STORE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        logging.exception('Failed to write floorplan store')
        return False


def _floorplan_payload(floor_id, polylines, sensors, air):
    return {
        'state': 'saved',
        'attributes': {
            'floor_id': floor_id,
            'polylines': polylines,
            'sensors': sensors,
            'sensor': sensors[0] if sensors else None,
            'air': air,
        },
    }


def _publish_floorplan_state(floor_id, polylines, sensors, air):
    try:
        response = ha_post(
            f'/states/{floorplan_entity_id(floor_id)}',
            _floorplan_payload(floor_id, polylines, sensors, air),
        )
        if response.status_code not in (200, 201):
            logging.warning('HA state update failed: %s', response.text)
    except Exception:
        logging.exception('HA state update failed for floor %s', floor_id)


def repair_floorplan_entry(stored, devices):
    """Resolve and enrich all radar references in one stored floorplan."""
    polylines = stored.get('polylines', [])
    sensors = stored.get('sensors')
    air = stored.get('air', [])
    if not sensors:
        legacy = stored.get('sensor')
        sensors = [legacy] if legacy else []

    sensors, sensors_changed, warnings = resolve_radar_references(
        sensors, devices, 'sensor'
    )
    air, air_changed, air_warnings = resolve_radar_references(
        air, devices, 'air marker'
    )
    warnings.extend(air_warnings)

    repaired = copy.deepcopy(stored)
    repaired['polylines'] = polylines
    repaired['sensors'] = sensors
    repaired['air'] = air
    if 'sensor' in repaired:
        repaired['sensor'] = sensors[0] if sensors else None
    return repaired, sensors_changed or air_changed, warnings


@app.route('/api/radar_devices', methods=['GET', 'POST'])
def radar_devices_route():
    try:
        return jsonify(discover_radar_devices())
    except Exception as e:
        logging.exception('radar_devices_route failed')
        return jsonify({'error': 'radar discovery failed', 'details': str(e)}), 502

@app.route('/api/template', methods=['GET', 'POST'])
def execute_template():
    try:
        if request.method == 'POST':
            data = request.get_json(force=True) or {}
            template = data.get('template', '')
        else:
            template = request.args.get('template', '')

        if not template:
            return jsonify({'error': 'template required'}), 400

        r = ha_post('/template', {'template': template})
        if r.status_code == 200:
            return Response(
                r.text,
                status=200,
                mimetype=r.headers.get('Content-Type', 'text/plain; charset=utf-8')
            )
        return jsonify({'error': 'template error', 'details': r.text}), r.status_code
    except Exception as e:
        logging.exception('execute_template failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/api/device_entities', methods=['POST'])
def device_entities():
    try:
        data = request.get_json(force=True) or {}
        dev = (data.get('device_id') or '').strip()
        if not dev:
            return jsonify({'error': 'device_id required'}), 400
        tpl = f"""
{{% set out = namespace(list=[]) %}}
{{% for s in states if (s.entity_id | device_id) == '{dev}' %}}
  {{% set out.list = out.list + [ {{
    'entity_id': s.entity_id,
    'domain': (s.entity_id.split('.'))[0],
    'state': s.state,
    'attributes': (s.attributes | tojson)
  }} ] %}}
{{% endfor %}}
{{{{ out.list | tojson }}}}
        """.strip()
        r = ha_post('/template', {'template': tpl})
        if r.status_code == 200:
            return Response(r.text, status=200, mimetype='application/json')
        return jsonify({'error': 'template error', 'details': r.text}), r.status_code
    except Exception as e:
        logging.exception('device_entities failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/api/floor_entities', methods=['GET', 'POST'])
def floor_entities_route():
    try:
        if request.method == 'POST':
            data = request.get_json(force=True) or {}
            floor = (data.get('floor')
                     or data.get('floor_id')
                     or data.get('floor_name')
                     or '').strip()
        else:
            floor = (request.args.get('floor')
                     or request.args.get('floor_id')
                     or request.args.get('floor_name')
                     or '').strip()
        if not floor:
            return jsonify({'error': 'floor (name_or_id) required'}), 400
        tpl = f"{{{{ floor_entities('{floor}') | tojson }}}}"
        r = ha_post('/template', {'template': tpl})
        if r.status_code == 200:
            return Response(r.text, status=200, mimetype='application/json')
        return jsonify({'error': 'template error', 'details': r.text}), r.status_code
    except Exception as e:
        logging.exception('floor_entities_route failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/api/floors', methods=['GET', 'POST'])
def floors_route():
    try:
        tpl = "{{ floors() | tojson }}"
        r = ha_post('/template', {'template': tpl})
        if r.status_code == 200:
            return Response(r.text, status=200, mimetype='application/json')
        return jsonify({'error': 'template error', 'details': r.text}), r.status_code
    except Exception as e:
        logging.exception('floors_route failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/api/floorplan', methods=['GET', 'POST'])
def floorplan_route():
    try:
        if request.method == 'GET':
            floor_id = (request.args.get('floor_id') or request.args.get('floor') or '').strip()
        else:
            data = request.get_json(force=True) or {}
            floor_id = (data.get('floor_id') or data.get('floor') or '').strip()
        if not floor_id:
            return jsonify({'error': 'floor_id required'}), 400

        if request.method == 'GET':
            store = load_store()
            stored = store.get(floor_id) or {}
            migration_warnings = []
            try:
                devices = discover_radar_devices()
                stored, changed, migration_warnings = repair_floorplan_entry(
                    stored, devices
                )
                if changed:
                    store[floor_id] = stored
                    if save_store(store):
                        _publish_floorplan_state(
                            floor_id,
                            stored.get('polylines', []),
                            stored.get('sensors', []),
                            stored.get('air', []),
                        )
                    else:
                        migration_warnings.append(
                            'Repaired radar references could not be persisted to disk'
                        )
            except Exception as e:
                logging.exception(
                    'Radar reference migration failed for floor %s', floor_id
                )
                migration_warnings.append(
                    f'Radar references could not be checked: {e}'
                )

            for warning in migration_warnings:
                logging.warning('Floor %s: %s', floor_id, warning)

            polylines = stored.get('polylines', [])
            sensors = stored.get('sensors')
            air = stored.get('air', [])
            if not sensors:
                legacy = stored.get('sensor')
                sensors = [legacy] if legacy else []
            first_sensor = sensors[0] if sensors else None
            return jsonify({
                'polylines': polylines,
                'sensors': sensors,
                'sensor': first_sensor,
                'air': air,
                'warnings': migration_warnings,
            })

        polylines = data.get('polylines', [])
        sensors = data.get('sensors')
        air = data.get('air', [])
        if sensors is None:
            legacy = data.get('sensor')
            sensors = [legacy] if legacy else []
        store = load_store()
        store[floor_id] = {'polylines': polylines, 'sensors': sensors, 'air': air}
        save_ok = save_store(store)

        _publish_floorplan_state(floor_id, polylines, sensors, air)

        if not save_ok:
            return jsonify({'error': 'failed to persist to disk'}), 500
        return jsonify({'ok': True})
    except Exception as e:
        logging.exception('floorplan_route failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/api/services/<domain>/<service>', methods=['POST'])
def call_service(domain, service):
    try:
        payload = request.get_json(force=True) or {}
        r = ha_post(f'/services/{domain}/{service}', payload)
        if r.status_code in (200, 201):
            return Response(r.text, status=r.status_code, mimetype='application/json')
        return jsonify({'error': 'service error', 'details': r.text}), r.status_code
    except Exception as e:
        logging.exception('call_service failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/api/historical_targets', methods=['POST'])
def historical_targets():
    try:
        import datetime
        data = request.get_json(force=True) or {}
        entity_ids = data.get('entity_ids', [])
        device_id = data.get('device_id', '').strip()

        if not entity_ids and not device_id:
            return jsonify({'error': 'device_id or entity_ids required'}), 400

        if not entity_ids:
            tpl = f"""
{{% set out = namespace(list=[]) %}}
{{% for s in states %}}
  {{% if (s.entity_id | device_id) == '{device_id}' %}}
    {{% set out.list = out.list + [ {{
      'entity_id': s.entity_id,
      'domain': (s.entity_id.split('.'))[0],
      'state': s.state,
      'attributes': (s.attributes | tojson)
    }} ] %}}
  {{% endif %}}
{{% endfor %}}
{{{{ out.list | tojson }}}}
            """.strip()
            r = ha_post('/template', {'template': tpl})
            if r.status_code != 200:
                return jsonify({'error': 'template error', 'details': r.text}), r.status_code
            arr = r.json() or []
            entity_ids = [
                e['entity_id']
                for e in arr
                if e['entity_id'].endswith('target_1_x')
                or e['entity_id'].endswith('target_1_y')
                or e['entity_id'].endswith('target_2_x')
                or e['entity_id'].endswith('target_2_y')
                or e['entity_id'].endswith('target_3_x')
                or e['entity_id'].endswith('target_3_y')
            ]

        if not entity_ids:
            return jsonify({'positions': []}), 200

        hours = data.get('hours', 24)
        now = datetime.datetime.utcnow()
        start_time = (now - datetime.timedelta(hours=hours))
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        entity_list_str = ','.join(entity_ids)
        history_url = f'/history/period/{start_str}?filter_entity_id={entity_list_str}'
        hr = requests.get(HOME_ASSISTANT_API + history_url, headers=headers)
        if hr.status_code != 200:
            return jsonify({'error': 'history fetch failed', 'status': hr.status_code}), hr.status_code

        history_data = hr.json()

        positions = {}
        for entity_list in history_data:
            if not entity_list:
                continue
            entity_id = entity_list[0]['entity_id']
            for entry in entity_list:
                last_changed = entry['last_changed']
                state = entry['state']
                try:
                    num_state = float(state)
                    if num_state == 0.0:
                        continue
                except ValueError:
                    continue

                parts = entity_id.split('_')
                target_num = parts[-2]
                axis = parts[-1]

                if axis not in ['x', 'y'] or target_num not in ['1', '2', '3']:
                    continue

                ts = last_changed[:19]

                if ts not in positions:
                    positions[ts] = {}
                if target_num not in positions[ts]:
                    positions[ts][target_num] = {}

                positions[ts][target_num][axis] = num_state

        pos_list = []
        for ts, targets in positions.items():
            for targ, coords in targets.items():
                if 'x' in coords and 'y' in coords and coords['x'] != 0 and coords['y'] != 0:
                    pos_list.append({
                        'target': targ,
                        'x': coords['x'],
                        'y': coords['y'],
                        'timestamp': ts
                    })

        return jsonify({'positions': pos_list}), 200

    except Exception as e:
        logging.exception('historical_targets failed')
        return jsonify({'error': 'backend exception', 'details': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('www', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) 
