#!/usr/bin/env python3
from flask import Flask, jsonify, request, Response, send_from_directory
import requests, os, sys, logging

app = Flask(__name__)

SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = os.getenv('HA_URL')
HA_TOKEN = os.getenv('HA_TOKEN')

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

@app.route('/api/template', methods=['POST'])
def execute_template():
    try:
        data = request.get_json(force=True) or {}
        template = data.get('template', '')
        if not template:
            return jsonify({'error': 'template required'}), 400
        r = ha_post('/template', {'template': template})
        if r.status_code == 200:
            return Response(r.text, status=200, mimetype=r.headers.get('Content-Type', 'text/plain; charset=utf-8'))
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
    'attributes': s.attributes
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

@app.route('/')
def index():
    return send_from_directory('www', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)