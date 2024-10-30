from flask import Flask, request, jsonify, render_template
import asyncio
from pysnmp.hlapi.v3arch.asyncio import *

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')  # Render the HTML template

@app.route('/snmp/control/<ip>/<community>/<port>', methods=['POST'])
async def control_port(ip, community, port):
    oid_ifAdminStatus = f'1.3.6.1.2.1.2.2.1.7.{port}'  # OID สำหรับ ifAdminStatus
    status = request.json.get('status')
    if status is None:
        return jsonify({"error": "Status not provided"}), 400

    # กำหนดสถานะใหม่เป็น 1 (ขึ้น) หรือ 2 (ลง)
    new_status = 1 if status == 'up' else 2  # 1 for up, 2 for down

    # ส่งคำสั่ง SNMP SET
    errorIndication, errorStatus, errorIndex, varBinds = await set_cmd(
        SnmpEngine(),
        CommunityData(community),
        await UdpTransportTarget.create((ip, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid_ifAdminStatus), Integer(new_status))
    )

    if errorIndication:
        print(f"Error Indication: {errorIndication}")
        return jsonify({"error": str(errorIndication)}), 400
    elif errorStatus:
        print(f"Error Status: {errorStatus.prettyPrint()} at {errorIndex}")
        return jsonify({"error": str(errorStatus.prettyPrint())}), 400


    return jsonify({"message": "Port status updated successfully."})

@app.route('/snmp/ports/<ip>/<community>', methods=['GET'])
async def get_ports(ip, community):
    oid_ifTable = '1.3.6.1.2.1.2.2.1.7'  # OID สำหรับ ifAdminStatus ของทุกพอร์ต
    errorIndication, errorStatus, errorIndex, varBinds = await bulk_cmd(
        SnmpEngine(),
        CommunityData(community),
        await UdpTransportTarget.create((ip, 161)),
        ContextData(),
        0,  # Non-repeaters
        10,  # Max-repetitions
        ObjectType(ObjectIdentity(oid_ifTable))
    )

    if errorIndication:
        return jsonify({"error": str(errorIndication)}), 400
    elif errorStatus:
        return jsonify({"error": str(errorStatus.prettyPrint())}), 400
    else:
        results = {}
        for name, value in varBinds:
            port_index = str(name).split('.')[-1]  # ดึงหมายเลขพอร์ต
            results[port_index] = str(value)  # เก็บสถานะพอร์ต
        return jsonify(results)  # ส่งกลับข้อมูลสถานะพอร์ต

if __name__ == '__main__':
    app.run(debug=True)
