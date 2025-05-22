import csv
import argparse
import sys

# Dictionary mapping op-codes to command names
commands = {
    0x06: 'WREN',
    0x04: 'WRDI',
    0xB9: 'SLEEP',
    0x05: 'RDSR',
    0x01: 'WRSR',
    0x9F: 'RDID',
    0x03: 'READ',
    0x02: 'WRITE',
    0x0B: 'FSTRD',
}

# Dictionary containing information about each command
command_info = {
    'WREN': {'command_length': 1, 'has_read_data': False, 'has_write_data': False},
    'WRDI': {'command_length': 1, 'has_read_data': False, 'has_write_data': False},
    'SLEEP': {'command_length': 1, 'has_read_data': False, 'has_write_data': False},
    'RDSR': {'command_length': 1, 'has_read_data': True, 'has_write_data': False},
    'WRSR': {'command_length': 2, 'has_read_data': False, 'has_write_data': False},
    'RDID': {'command_length': 1, 'has_read_data': True, 'has_write_data': False},
    'READ': {'command_length': 4, 'has_read_data': True, 'has_write_data': False},
    'WRITE': {'command_length': 4, 'has_read_data': False, 'has_write_data': True},
    'FSTRD': {'command_length': 5, 'has_read_data': True, 'has_write_data': False},
}

# Descriptions for commands without data
command_descriptions = {
    'WREN': 'Set Write Enable Latch',
    'WRDI': 'Reset Write Enable Latch',
    'SLEEP': 'Enter Sleep Mode',
    'RDSR': 'Read Status Register',
    'WRSR': 'Write Status Register',
    'RDID': 'Read Device ID',
    'READ': 'Read Memory',
    'WRITE': 'Write Memory',
    'FSTRD': 'Fast Read Memory',
}

def hex_to_ascii(hex_list):
    """Convert a list of hex strings to ASCII, keeping non-printable chars as hex."""
    ascii_str = ''
    for hex_val in hex_list:
        try:
            val = int(hex_val, 16)
            # Check if the value is printable ASCII (32 to 126)
            if 32 <= val <= 126:
                ascii_str += chr(val)
            else:
                ascii_str += f"0x{hex_val}"
        except ValueError:
            ascii_str += f"0x{hex_val}"
    return ascii_str

def generate_descriptions(op_code, mosi_row, miso_row):
    """Generate human-readable descriptions for MOSI and MISO rows based on the op-code."""
    if op_code not in commands:
        return f"Invalid command: 0x{op_code:02X}", "Unknown"

    command = commands[op_code]
    info = command_info[command]
    command_length = info['command_length']
    #has_read_data = info['has_read_data']
    #has_write_data = info['has_write_data']

    if len(mosi_row) < command_length:
        return f"{command} command (insufficient bytes)", "Unknown"

    # Extract address if applicable
    address_str = None
    if command in ['READ', 'WRITE', 'FSTRD'] and len(mosi_row) >= 4:
        try:
            address = (int(mosi_row[1], 16) << 16) | (int(mosi_row[2], 16) << 8) | int(mosi_row[3], 16)
            address_str = f"0x{address:06X}"
        except ValueError:
            address_str = "invalid"

    # Generate descriptions
    if command == 'WRSR':
        if len(mosi_row) >= 2:
            status = mosi_row[1]
            description_mosi = f"WRSR: Write Status Register, value: 0x{status}"
        else:
            description_mosi = "WRSR: Write Status Register (insufficient bytes)"
        description_miso = "No data"
    elif command == 'RDSR':
        description_mosi = "RDSR: Read Status Register"
        if len(miso_row) > command_length:
            status = miso_row[command_length]
            description_miso = f"Status register: 0x{status}"
        else:
            description_miso = "No data"
    elif command == 'RDID':
        description_mosi = "RDID: Read Device ID"
        if len(miso_row) >= command_length + 4:
            id_bytes = miso_row[command_length:command_length+4]
            id_str = ','.join([f"0x{b}" for b in id_bytes])
            description_miso = f"Device ID: {id_str}"
        else:
            description_miso = "Device ID (insufficient bytes)"
    elif command == 'READ':
        description_mosi = f"{command} command"
        if address_str:
            description_mosi += f", address: {address_str}"
        if len(miso_row) > command_length:
            data = miso_row[command_length:]
            data_str = ','.join(data)
            ascii_str = hex_to_ascii(data)
            description_miso = f"Data read: {data_str} (ASCII: {ascii_str})"
        else:
            description_miso = "No data"
    elif command == 'WRITE':
        description_mosi = f"{command} command"
        if address_str:
            description_mosi += f", address: {address_str}"
        if len(mosi_row) > command_length:
            data = mosi_row[command_length:]
            data_str = ','.join(data)
            ascii_str = hex_to_ascii(data)
            description_mosi += f", data: {data_str} (ASCII: {ascii_str})"
        else:
            description_mosi += " (no data)"
        description_miso = "No data"
    elif command == 'FSTRD':
        description_mosi = f"{command} command"
        if address_str:
            description_mosi += f", address: {address_str}"
        if len(miso_row) > command_length:
            data = miso_row[command_length:]
            data_str = ','.join(data)
            ascii_str = hex_to_ascii(data)
            description_miso = f"Data read: {data_str} (ASCII: {ascii_str})"
        else:
            description_miso = "No data"
    else:
        description_mosi = f"{command}: {command_descriptions[command]}"
        description_miso = "No data"

    return description_mosi, description_miso

def process_pairs(input_file, output_file):
    """Process CSV in pairs of rows: MISO followed by MOSI."""
    with open(input_file, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        for i in range(0, len(rows), 2):
            if i + 1 >= len(rows):
                break  # Skip if no MOSI row
            miso_row = rows[i]
            mosi_row = rows[i + 1]
            if len(mosi_row) == 0 or len(miso_row) == 0:
                continue
            try:
                op_code = int(mosi_row[0], 16)
            except ValueError:
                continue
            description_mosi, description_miso = generate_descriptions(op_code, mosi_row, miso_row)
            new_miso_row = [description_miso] + miso_row
            new_mosi_row = [description_mosi] + mosi_row
            writer.writerow(new_miso_row)
            writer.writerow(new_mosi_row)

def main():
    """Main function to parse arguments and process the CSV."""
    parser = argparse.ArgumentParser(description="Analyze SPI signal data from MB85RS4MT FeRAM chip.")
    parser.add_argument("--input", default="input.csv", help="Input CSV file")
    parser.add_argument("--output", default="output.csv", help="Output CSV file")
    parser.add_argument("--format", choices=["pairs", "labeled"], default="pairs", help="Format of the CSV file")
    args = parser.parse_args()

    if args.format == "pairs":
        process_pairs(args.input, args.output)
    else:
        print("Labeled format not implemented yet. Please modify the script to handle labeled rows.")
        sys.exit(1)

if __name__ == "__main__":
    main()