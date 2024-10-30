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
    else:
        print(f"Successfully set port {port} to {'up' if new_status == 1 else 'down'}")

    return jsonify({"message": "Port status updated successfully."})

@app.route('/snmp/ports/<ip>/<community>', methods=['GET'])
async def get_ports(ip, community):
    oid_ifTable = '1.3.6.1.2.1.2.2.1.7'  # OID สำหรับ ifAdminStatus ของทุกพอร์ต
    oid_ifDescr = '1.3.6.1.2.1.2.2.1.2'  # OID สำหรับ ifDescr (ชื่อพอร์ต)

    errorIndication, errorStatus, errorIndex, varBinds_admin = await bulk_cmd(
        SnmpEngine(),
        CommunityData(community),
        await UdpTransportTarget.create((ip, 161)),
        ContextData(),
        0,  # Non-repeaters
        10,  # Max-repetitions
        ObjectType(ObjectIdentity(oid_ifTable))
    )

    errorIndication_descr, errorStatus_descr, errorIndex_descr, varBinds_descr = await bulk_cmd(
        SnmpEngine(),
        CommunityData(community),
        await UdpTransportTarget.create((ip, 161)),
        ContextData(),
        0,  # Non-repeaters
        10,  # Max-repetitions
        ObjectType(ObjectIdentity(oid_ifDescr))
    )

    if errorIndication:
        return jsonify({"error": str(errorIndication)}), 400
    elif errorStatus:
        return jsonify({"error": str(errorStatus.prettyPrint())}), 400
    elif errorIndication_descr:
        return jsonify({"error": str(errorIndication_descr)}), 400
    elif errorStatus_descr:
        return jsonify({"error": str(errorStatus_descr.prettyPrint())}), 400
    else:
        results = {}
        # Create a mapping for port names
        port_names = {}
        for name, value in varBinds_descr:
            port_index = str(name).split('.')[-1]  # ดึงหมายเลขพอร์ต
            port_names[port_index] = str(value)  # เก็บชื่อพอร์ต

        for name, value in varBinds_admin:
            port_index = str(name).split('.')[-1]  # ดึงหมายเลขพอร์ต
            results[port_index] = {
                "status": str(value),  # เก็บสถานะพอร์ต
                "name": port_names.get(port_index, "Unknown Port")  # เก็บชื่อพอร์ต
            }

        return jsonify(results)  # ส่งกลับข้อมูลสถานะพอร์ต

@app.route('/snmp/device-name/<ip>/<community>', methods=['GET'])
async def get_device_name(ip, community):
    oid_sysName = '1.3.6.1.2.1.1.5.0'  # OID for sysName (device name)
    errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
        SnmpEngine(),
        CommunityData(community),
        await UdpTransportTarget.create((ip, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid_sysName))
    )

    if errorIndication:
        return jsonify({"error": str(errorIndication)}), 400
    elif errorStatus:
        return jsonify({"error": str(errorStatus.prettyPrint())}), 400
    else:
        device_name = str(varBinds[0][1])
        return jsonify({"device_name": device_name})


if __name__ == '__main__':
    app.run(debug=True)
