from flask import Flask, jsonify, request, Response, send_from_directory
import requests, os, sys, logging, json, re

app = Flask(__name__)

SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = os.getenv('HA_URL')
HA_TOKEN = os.getenv('HA_TOKEN')
FLOORPLAN_STORE = os.getenv('FLOORPLAN_STORE', '/data/zone_editor_floorplans.json')

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

        entity_id = floorplan_entity_id(floor_id)

        if request.method == 'GET':
            store = load_store()
            stored = store.get(floor_id) or {}
            polylines = stored.get('polylines', [])
            sensors = stored.get('sensors')
            if not sensors:
                legacy = stored.get('sensor')
                if legacy:
                    sensors = [legacy]
                else:
                    sensors = []
            first_sensor = sensors[0] if sensors else None
            return jsonify({'polylines': polylines, 'sensors': sensors, 'sensor': first_sensor})

        polylines = data.get('polylines', [])
        sensors = data.get('sensors')
        if sensors is None:
            legacy = data.get('sensor')
            sensors = [legacy] if legacy else []
        payload = {
            'state': 'saved',
            'attributes': {
                'floor_id': floor_id,
                'polylines': polylines,
                'sensors': sensors,
                'sensor': sensors[0] if sensors else None
            }
        }
        store = load_store()
        store[floor_id] = {'polylines': polylines, 'sensors': sensors}
        save_ok = save_store(store)

        r = ha_post(f'/states/{entity_id}', payload)
        if r.status_code not in (200, 201):
            logging.warning('HA state update failed: %s', r.text)

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