import os
import xlrd
import json
import cantools

from cantools.database import Database, Node, Message, Signal
from cantools.database.can.bus import Bus
from cantools.database.can.formats.dbc import DbcSpecifics, AttributeDefinition, Attribute

ATT_DEF = {
    'Manufacturer': AttributeDefinition('Manufacturer', type_name='STRING'),
    'NmType': AttributeDefinition('NmType', default_value='NmAsr', type_name='STRING'),
    'BusType': AttributeDefinition('BusType', default_value='CAN', type_name='STRING'),
    'Baudrate': AttributeDefinition('Baudrate', default_value=500000, type_name='INT', minimum=0,
                                    maximum=1000000),
    'NmAsrRepeatMessageTime': AttributeDefinition('NmAsrRepeatMessageTime', default_value=3200, type_name='INT',
                                                  minimum=0, maximum=65535),
    'NmAsrCanMsgCycleTime': AttributeDefinition('NmAsrCanMsgCycleTime', default_value=640, type_name='INT',
                                                minimum=0, maximum=65535),
    'NmAsrWaitBusSleepTime': AttributeDefinition('NmAsrWaitBusSleepTime', default_value=1500, type_name='INT',
                                                 minimum=0, maximum=65535),
    'NmAsrTimeoutTime': AttributeDefinition('NmAsrTimeoutTime', default_value=2000, type_name='INT', minimum=0,
                                            maximum=65535),
    'NmAsrMessageCount': AttributeDefinition('NmAsrMessageCount', default_value=128, type_name='INT', minimum=0,
                                             maximum=256),
    'NmAsrBaseAddress': AttributeDefinition('NmAsrBaseAddress', default_value=1280, type_name='HEX', minimum=0,
                                            maximum=2047),
    'DBName': AttributeDefinition('DBName', default_value="", type_name='STRING'),
    'GenSigTimeoutTime_ALL': AttributeDefinition('GenSigTimeoutTime_ALL', default_value=0, kind='SG_',
                                                 type_name='INT', minimum=0, maximum=65535),
    'GenSigStartValue': AttributeDefinition('GenSigStartValue', default_value=0, kind='SG_', type_name='INT',
                                            minimum=0, maximum=65535),
    'ECU': AttributeDefinition('ECU', kind='BU_', type_name='STRING'),
    'Version': AttributeDefinition('Version', kind='BU_', type_name='STRING'),
    'NmAsrCanMsgReducedTime': AttributeDefinition('NmAsrCanMsgReducedTime', default_value=320, kind='BU_',
                                                  type_name='INT', minimum=320, maximum=640),
    'NmAsrCanMsgCycleOffset': AttributeDefinition('NmAsrCanMsgCycleOffset', default_value=0, kind='BU_',
                                                  type_name='INT', minimum=0, maximum=65535),
    'NmAsrNodeIdentifier': AttributeDefinition('NmAsrNodeIdentifier', default_value=0, kind='BU_', type_name='HEX',
                                               minimum=0, maximum=255),
    'NmAsrNode': AttributeDefinition('NmAsrNode', default_value='Yes', kind='BU_', type_name='ENUM',
                                     choices=["No", "Yes"]),
    'ILUsed': AttributeDefinition('ILUsed', default_value='Yes', kind='BU_', type_name='ENUM',
                                  choices=["No", "Yes"]),
    'TpSTMin': AttributeDefinition('TpSTMin', default_value=20, kind='BU_', type_name='INT', minimum=0,
                                   maximum=255),
    'Address': AttributeDefinition('Address', default_value=0, kind='BU_', type_name='HEX', minimum=0, maximum=255),
    'NmStationAddress': AttributeDefinition('NmStationAddress', default_value=0, kind='BU_', type_name='INT',
                                            minimum=0, maximum=0),
    'GenMsgCycleTime': AttributeDefinition('GenMsgCycleTime', default_value=0, kind='BO_', type_name='INT',
                                           minimum=0, maximum=65535),
    'GenMsgCycleTimeFast': AttributeDefinition('GenMsgCycleTimeFast', default_value=0, kind='BO_', type_name='INT',
                                               minimum=0, maximum=65535),
    'GenMsgNrOfRepetition': AttributeDefinition('GenMsgNrOfRepetition', default_value=0, kind='BO_',
                                                type_name='INT', minimum=0, maximum=65535),
    'GenMsgDelayTime': AttributeDefinition('GenMsgDelayTime', default_value=0, kind='BO_', type_name='INT',
                                           minimum=0, maximum=65535),
    'GenMsgStartDelayTime': AttributeDefinition('GenMsgStartDelayTime', default_value=0, kind='BO_',
                                                type_name='INT', minimum=0, maximum=65535),
    'DiagUudtResponse': AttributeDefinition('DiagUudtResponse', default_value='No', kind='BO_', type_name='ENUM',
                                            choices=["No", "Yes"]),
    'DiagState': AttributeDefinition('DiagState', default_value='No', kind='BO_', type_name='ENUM',
                                     choices=["No", "Yes"]),
    'NmAsrMessage': AttributeDefinition('NmAsrMessage', default_value='No', kind='BO_', type_name='ENUM',
                                        choices=["No", "Yes"]),
    'DiagRequest': AttributeDefinition('DiagRequest', default_value='No', kind='BO_', type_name='ENUM',
                                       choices=["No", "Yes"]),
    'DiagResponse': AttributeDefinition('DiagResponse', default_value='No', kind='BO_', type_name='ENUM',
                                        choices=["No", "Yes"]),
    'GenMsgILSupport': AttributeDefinition('GenMsgILSupport', default_value='No', kind='BO_', type_name='ENUM',
                                           choices=["No", "Yes"]),
    'GenSigSendType': AttributeDefinition('GenSigSendType', default_value='Cycle', kind='SG_', type_name='ENUM',
                                          choices=["Cycle", "OnWrite", "OnWriteWithRepetition", "OnChange",
                                                   "OnChangeWithRepetition", "IfActive", "IfActiveWithRepetition",
                                                   "NoSigSendType"]),
    'GenMsgSendType': AttributeDefinition('GenMsgSendType', default_value='Cycle', kind='BO_', type_name='ENUM',
                                          choices=["Cycle", "Event", "IfActive", "CE", "CA", "NoMsgSendType"])
}


def signal_creation(sg_name, start_bit, sig_len_in_bit, byte_order_of_signal, data_type, initial_value, scale, offset,
                    signal_min, signal_max, unit, sg_desc, receivers, sg_send_type, sg_value_desc):
    byte_order = 'big_endian' if 'motorola' in byte_order_of_signal.lower() else 'little_endian'
    is_signed = 'unsigned' not in data_type.lower()
    is_float = 'float' in data_type.lower() or 'double' in data_type.lower()

    # set attribute signal send type
    sig_send_types = ATT_DEF['GenSigSendType'].choices
    sg_send_type = sig_send_types.index(sg_send_type) if sg_send_type in sig_send_types else len(sg_send_type) - 1
    attributes = {0: Attribute(sg_send_type, ATT_DEF['GenSigSendType'])}

    # set value table for the signal, assume the format below:
    # {value1} "{String1}" \n
    # {value1} "{String1}" \n ...
    choices = {}
    for each_line in sg_value_desc.split("\n"):
        list_each_line = each_line.split('"')
        if len(list_each_line) > 2:
            choices.update({int(list_each_line[0]): list_each_line[1]})

    dbc_specifics = DbcSpecifics(attribute_definitions=ATT_DEF, attributes=attributes)

    return Signal(sg_name, start_bit, sig_len_in_bit, byte_order=byte_order, is_signed=is_signed,
                  initial=initial_value, scale=scale, offset=offset, minimum=signal_min, maximum=signal_max,
                  unit=unit, choices=choices, dbc_specifics=dbc_specifics, comment=sg_desc, receivers=receivers,
                  is_float=is_float)


def msg_creation(can_id, msg_name, msg_len, signals, senders, msg_type, cycle, cycle_fast, msg_repeat, delay,
                 msg_send_type):
    attributes = {}
    msg_send_types = ATT_DEF['GenMsgSendType'].choices
    if msg_type.lower() == "diag":
        attributes.update({0: Attribute(len(msg_send_types) - 1, ATT_DEF['GenMsgSendType'])})
        if 'diagreq' in msg_name.lower():
            attributes.update({1: Attribute(1, ATT_DEF['DiagRequest'])})
        if 'diagresp' in msg_name.lower():
            attributes.update({1: Attribute(1, ATT_DEF['DiagResponse'])})
        else:
            attributes.update({1: Attribute(1, ATT_DEF['DiagState'])})
    elif msg_type.lower() == "nm":
        attributes.update({0: Attribute(0, ATT_DEF['GenMsgSendType']),
                           1: Attribute(1, ATT_DEF['NmAsrMessage']),
                           2: Attribute(cycle, ATT_DEF['GenMsgCycleTime'])})
    else:
        # normal messages
        msti = msg_send_types.index(msg_send_type) if msg_send_type in msg_send_types else len(msg_send_types) - 1
        attributes.update({0: Attribute(msti, ATT_DEF['GenMsgSendType']),
                           1: Attribute(cycle, ATT_DEF['GenMsgCycleTime']),
                           2: Attribute(cycle_fast, ATT_DEF['GenMsgCycleTimeFast']),
                           3: Attribute(msg_repeat, ATT_DEF['GenMsgNrOfRepetition']),
                           4: Attribute(delay, ATT_DEF['GenMsgDelayTime'])})

    dbc_specifics = DbcSpecifics(attribute_definitions=ATT_DEF, attributes=attributes)
    return Message(can_id, msg_name, msg_len, signals=signals, dbc_specifics=dbc_specifics, senders=senders,
                   cycle_time=cycle)


def dbc_creation(busName, busLongName, baudrate):
    buses = [Bus(busName, comment=busLongName, baudrate=baudrate)]
    attributes = {0: Attribute(busName, ATT_DEF['DBName']), 1: Attribute(baudrate, ATT_DEF['Baudrate'])}
    dbc_specifics = DbcSpecifics(attribute_definitions=ATT_DEF, attributes=attributes)
    db = Database(dbc_specifics=dbc_specifics, buses=buses)
    return db


def xls2dbc(config):
    with open(config, 'r') as f:
        config = json.load(f)
        try:
            os.mkdir(config['outputFolder'])
        except:
            pass

        for netName, inputFile in config['inputNetworks']['inputNetworkFiles'].items():
            if 'CAN' in netName:
                form = config['inputNetworks']['inputNetworkFileFormatCAN']
                input_file_path = config['inputFolder'] + '\\' + inputFile
                output_file_path = config['outputFolder'] + '\\' + os.path.splitext(inputFile)[0] + '.dbc'
                net_long_name = config['inputNetworks']['inputNetworksNames'][netName]
                net_baudrate = config['inputNetworks']['inputNetworkBaudrate']
                sheets = config['inputNetworks']['inputNetWorkSheets']

                workbook = xlrd.open_workbook(input_file_path)
                database = dbc_creation(netName, net_long_name, net_baudrate)

                for sheetIdx in sheets:
                    sheet = workbook.sheet_by_index(sheetIdx)
                    ecus = sheet.row_values(0, start_colx=form["StartOfECUListCol"])
                    for node in ecus:
                        database.nodes.append(Node(node, comment=node))

                    signals = []
                    current_msg = ""
                    can_id = 0
                    msg_len = 0
                    senders = []
                    cycle = 0
                    msg_type = ""
                    c_fast = 0
                    msg_repeat = 0
                    delay = 0
                    msg_send_type = ""
                    for i in range(form["FirstRow"], sheet.nrows):
                        row = sheet.row_values(i, end_colx=form["StartOfECUListCol"])
                        ecus_access = sheet.row_values(i, start_colx=form["StartOfECUListCol"])

                        if row[form["MsgName"]] != "" and row[form["SignalName"]] == "":
                            # message row handling, update the previous message to the dbc
                            if current_msg != row[form["MsgName"]] and current_msg != "" and len(signals) != 0:
                                msg = msg_creation(can_id, current_msg, msg_len, signals, senders, msg_type, cycle,
                                                   c_fast, msg_repeat, delay, msg_send_type)
                                database.messages.append(msg)
                                database.refresh()
                                signals = []

                            # get the new message info
                            current_msg = row[form["MsgName"]]
                            can_id = int(row[form["MsgID"]], 16)
                            msg_len = int(row[form["MsgLengthInByte"]])
                            senders = [ecus[ecus_access.index('s')]] if 's' in ecus_access else None
                            msg_type = row[form["MsgType"]]
                            cycle = int(row[form["MsgCycleTime"]]) if row[form["MsgCycleTime"]] != "" else 0
                            c_fast = int(row[form["MsgCycleTimeFast"]]) if row[form["MsgCycleTimeFast"]] != "" else 0
                            msg_repeat = int(row[form["MsgNoOfReption"]]) if row[form["MsgNoOfReption"]] != "" else 0
                            delay = int(row[form["MsgDelayTime"]]) if row[form["MsgDelayTime"]] != "" else 0
                            msg_send_type = row[form["MsgSendType"]]

                        elif row[form["MsgName"]] == "" and row[form["SignalName"]] != "":
                            # signal row handling, get the current message and add signals to it
                            sg_name = row[form["SignalName"]]
                            start_bit = int(row[form["StartBit"]])
                            sig_len = int(row[form["SignalLengthInBit"]])
                            byte_order = row[form["ByteOrder"]]
                            data_type = row[form["DataType"]]
                            initial_value = int(row[form["InitialValue"]], 16) if row[form["InitialValue"]] != "" else 0
                            scale = row[form["Resolution"]]
                            offset = row[form["Offset"]]
                            signal_min = row[form["SignalMin.ValuePhys"]]
                            signal_max = row[form["SignalMax.ValuePhys"]]
                            unit = row[form["Unit"]]
                            sg_desc = row[form["SignalDescription"]]
                            receivers = [ecus[ecus_access.index('r')]] if 'r' in ecus_access else None

                            # dbc specifics
                            sg_send_type = row[form["SignalSendType"]]
                            sg_value_desc = row[form["SignalValueDescription"]]

                            sg = signal_creation(sg_name, start_bit, sig_len, byte_order, data_type, initial_value,
                                                 scale, offset, signal_min, signal_max, unit, sg_desc, receivers,
                                                 sg_send_type, sg_value_desc)
                            signals.append(sg)

                # add the last message to the dbc
                if current_msg != "" and len(signals) != 0:
                    msg = msg_creation(can_id, current_msg, msg_len, signals, senders, msg_type, cycle, c_fast,
                                       msg_repeat, delay, msg_send_type)
                    database.messages.append(msg)
                    database.refresh()

                with open(output_file_path, 'w') as create_empty_file:
                    cantools.database.dump_file(database, output_file_path)
        # elif 'LIN' in netName:
        # TODO: to generate ldf files


xls2dbc("project.json")
