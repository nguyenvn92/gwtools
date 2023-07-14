import os
import xlrd
import json
import xml.etree.ElementTree as ET

# in-place prettyprint formatter,
# from stackoverflow.com/questions/749796/pretty-printing-xml-in-python
def indent(elem, level=0):
    i = "\n" + level*" "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# create the cantp connections
def cantp_creation(root, cantp_conf_phys, cantp_conf_func):
    tpconnections = ET.SubElement(root, 'TP-CONNECTIONS')
    for (key, value) in cantp_conf_phys.items():
        # 1st direction
        tpconnection = ET.SubElement(tpconnections, 'CAN-TP-CONNECTION')
        shortname = ET.SubElement(tpconnection, 'SHORT-NAME')
        can_cluster_ref = ET.SubElement(tpconnection, 'CAN-CLUSTER-REF')
        data_pdu_ref = ET.SubElement(tpconnection, 'DATA-PDU-REF')
        flow_control_pdu_ref = ET.SubElement(tpconnection, 'FLOW-CONTROL-PDU-REF')
        shortname.text = key + "__" + value[0] + "__" + value[1]
        can_cluster_ref.text = key
        data_pdu_ref.text = value[0]
        flow_control_pdu_ref.text = value[1]
        # 2nd direction
        tpconnection = ET.SubElement(tpconnections, 'CAN-TP-CONNECTION')
        shortname = ET.SubElement(tpconnection, 'SHORT-NAME')
        can_cluster_ref = ET.SubElement(tpconnection, 'CAN-CLUSTER-REF')
        data_pdu_ref = ET.SubElement(tpconnection, 'DATA-PDU-REF')
        flow_control_pdu_ref = ET.SubElement(tpconnection, 'FLOW-CONTROL-PDU-REF')
        shortname.text = key + "__" + value[1] + "__" + value[0]
        can_cluster_ref.text = key
        data_pdu_ref.text = value[1]
        flow_control_pdu_ref.text = value[0]
    for (key, value) in cantp_conf_func.items():
        for pdu in value:
            tpconnection = ET.SubElement(tpconnections, 'CAN-TP-CONNECTION')
            shortname = ET.SubElement(tpconnection, 'SHORT-NAME')
            can_cluster_ref = ET.SubElement(tpconnection, 'CAN-CLUSTER-REF')
            data_pdu_ref = ET.SubElement(tpconnection, 'DATA-PDU-REF')
            shortname.text = key + "__" + pdu
            can_cluster_ref.text = key
            data_pdu_ref.text = pdu
    return tpconnections


def gateway_routing_creation(root, form, ecu, netnames, cantp_conf_func, input_file_path, sheets):
    gwrouting = ET.SubElement(root, 'GATEWAY-ROUTING')
    tp_routes = {}  # dict {ecu, src_tp_conn, dest_tp_conn}
    msg_routes = {}  # dict {ecu, src_network, dest_network, src_pdu, dest_pdu, src_signals}
    sig_routes = {}  # dict {ecu, src_network, dest_network, src_pdu, dest_pdu, src_signal, dest_signal}
    inv_netnames = {v: k for k, v in netnames.items()}
    workbook = xlrd.open_workbook(input_file_path)
    for sheetIdx in sheets:
        sheet = workbook.sheet_by_index(sheetIdx)
        for i in range(form["FirstRow"], sheet.nrows):
            row = sheet.row_values(i)
            if row[form["DestNetwork"]] in inv_netnames and row[form["SrcNetwork"]] in inv_netnames:
                dest_network = inv_netnames[row[form["DestNetwork"]]]
                src_network = inv_netnames[row[form["SrcNetwork"]]]
                dest_msg = row[form["DestMsgName"]]
                src_msg = row[form["SrcMsgName"]]
                if dest_msg in cantp_conf_func[dest_network] and src_msg in cantp_conf_func[src_network]:
                    key = ecu + src_network + src_msg + dest_network + dest_msg
                    if key not in tp_routes:
                        tp_routes.update({key: [ecu, src_network + "__" + src_msg, dest_network + "__" + dest_msg]})
                elif row[form["RoutingType"]] == "Msg":
                    key = ecu + src_network + dest_network + src_msg + dest_msg
                    src_signal = row[form["SrcSigName"]]
                    if key not in msg_routes:
                        src_signals = [src_signal] if row[form["SrcSigName"]] != "" else []
                        msg_routes.update({key: [ecu, src_network, dest_network, src_msg, dest_msg, src_signals]})
                    else:
                        if src_signal != "":
                            lst = msg_routes[key][-1]
                            lst.append(src_signal)
                            updated_msg = [ecu, src_network, dest_network, src_msg, dest_msg,
                                           lst]
                            msg_routes.update({key: updated_msg})
                else:
                    if row[form["SrcSigName"]] != "" and row[form["DestSigName"]]:
                        src_signal = row[form["SrcSigName"]]
                        dest_signal = row[form["DestSigName"]]
                        key = ecu + src_network + dest_network + src_msg + dest_msg + src_signal + dest_signal
                        if key not in sig_routes:
                            sig_routes.update({key: [ecu, src_network, dest_network, src_msg, dest_msg, src_signal,
                                                     dest_signal]})
    for key in sorted(tp_routes.keys()):
        each = tp_routes[key]
        tprouting = ET.SubElement(gwrouting, 'TP-HIGH-LEVEL-ROUTING')
        ecu_ins = ET.SubElement(tprouting, 'ECU-INSTANCE-REF')
        src = ET.SubElement(tprouting, 'SOURCE-CAN-TP-CONNECTION-REF')
        dest = ET.SubElement(tprouting, 'TARGET-CAN-TP-CONNECTION-REF')
        ecu_ins.text = each[0]
        src.text = each[1]
        dest.text = each[2]
    for key in sorted(msg_routes.keys()):
        each = msg_routes[key]
        msgrouting = ET.SubElement(gwrouting, 'PDUR-MESSAGE-ROUTING')
        ecu_ins = ET.SubElement(msgrouting, 'ECU-INSTANCE-REF')
        src_network = ET.SubElement(msgrouting, 'SOURCE-CAN-CLUSTER-REF')
        dest_network = ET.SubElement(msgrouting, 'TARGET-CAN-CLUSTER-REF')
        ipdu_mappings = ET.SubElement(msgrouting, 'I-PDU-MAPPINGS')
        ipdu_mapping = ET.SubElement(ipdu_mappings, 'I-PDU-MAPPING')
        route_dlc = ET.SubElement(ipdu_mapping, 'ROUTE-DLC')
        src_msg = ET.SubElement(ipdu_mapping, 'SOURCE-I-PDU-REF')
        src_signals = ET.SubElement(ipdu_mapping, 'SOURCE-SIGNALS')
        for sig in each[-1]:
            sys_signal = ET.SubElement(src_signals, 'SYSTEM-SIGNAL-REF')
            sys_signal.text = sig
        dest_msg = ET.SubElement(ipdu_mapping, 'TARGET-I-PDU-REF')
        ecu_ins.text = each[0]
        src_network.text = each[1]
        dest_network.text = each[2]
        route_dlc.text = 'true'
        src_msg.text = each[3]
        dest_msg.text = each[4]
    for key in sorted(sig_routes.keys()):
        each = sig_routes[key]
        sigrouting = ET.SubElement(gwrouting, 'COM-SIGNAL-ROUTING')
        ecu_ins = ET.SubElement(sigrouting, 'ECU-INSTANCE-REF')
        src_network = ET.SubElement(sigrouting, 'SOURCE-LIN-CLUSTER-REF') if 'LIN' in each[1] else ET.SubElement(
            sigrouting, 'SOURCE-CAN-CLUSTER-REF')
        dest_network = ET.SubElement(sigrouting, 'TARGET-LIN-CLUSTER-REF') if 'LIN' in each[2] else ET.SubElement(
            sigrouting, 'SOURCE-CAN-CLUSTER-REF')
        signal_mappings = ET.SubElement(sigrouting, 'SIGNAL-MAPPINGS')
        signal_mapping = ET.SubElement(signal_mappings, 'SIGNAL-MAPPING')
        process = ET.SubElement(signal_mapping,'PROCESSING')
        src_msg = ET.SubElement(signal_mapping, 'SOURCE-I-PDU-REF')
        src_sig = ET.SubElement(signal_mapping, 'SOURCE-SIGNAL-REF')
        dest_msg = ET.SubElement(signal_mapping, 'TARGET-SIGNAL-REF')
        dest_sig = ET.SubElement(signal_mapping, 'TARGET-SIGNAL-REF')
        ecu_ins.text = each[0]
        src_network.text = each[1]
        dest_network.text = each[2]
        process.text = 'DEFERED'
        src_msg.text = each[3]
        dest_msg.text = each[4]
        src_sig.text = each[5]
        dest_sig.text = each[6]
    return gwrouting


def xls2vsde(config):
    with open(config, 'r') as f:
        config = json.load(f)
        try:
            os.mkdir(config['outputFolder'])
        except:
            pass
        form = config['routingTable']['inputRoutingTableFormat']
        input_file = config['routingTable']['inputRoutingTableFile']
        input_file_path = config['inputFolder'] + '\\' + input_file
        output_file_path = config['outputFolder'] + '\\' + os.path.splitext(input_file)[0] + '.vsde'
        attributes = {'xmlns': 'http://www.vector-informatik.de/ExtractExtension',
                      'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                      'xsi:schemaLocation': 'http://www.vector-informatik.de/ExtractExtension ExtractExtension.xsd'}
        root = ET.Element('EXTRACT-EXTENSION', attrib=attributes)
        cantp_conf_phys = config['routingTable']['inputDiagPhys']
        cantp_conf_func = config['routingTable']['inputDiagFunc']
        tpconnections = cantp_creation(root, cantp_conf_phys, cantp_conf_func)
        gwrouting = gateway_routing_creation(root, form, config["EcuInstance"], config['NetworksNames'],
                                             cantp_conf_func, input_file_path,
                                             config["routingTable"]["inputRoutingTableWorkingSheets"])
        indent(root)
        tree = ET.ElementTree(root)
        tree.write(output_file_path, encoding="utf-8", xml_declaration=True)


xls2vsde("project.json")
