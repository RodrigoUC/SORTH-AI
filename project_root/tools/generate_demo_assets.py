"""Rebuild original icon and synthetic JSON sources using only Python's stdlib."""
import argparse
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Original geometric timetable mark. No imported paths, fonts or image pixels.
RECTS = [(0, 0, 64, 64, '#183153'), (10, 12, 44, 42, '#FFFFFF'),
         (10, 12, 44, 9, '#087F83'), (17, 7, 5, 11, '#FFFFFF'),
         (42, 7, 5, 11, '#FFFFFF'), (16, 27, 19, 8, '#087F83'),
         (39, 27, 9, 8, '#6545AD'), (16, 39, 9, 8, '#6545AD'),
         (29, 39, 19, 8, '#087F83')]


def icon_svg():
    shapes = ''.join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>'
                     for x, y, w, h, c in RECTS)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" '
            'viewBox="0 0 64 64"><title>SORTH timetable</title>' + shapes + '</svg>\n').encode()


def icon_png(size):
    pixels = bytearray()
    for row in range(size):
        pixels.append(0)
        for col in range(size):
            color = '#183153'
            for x, y, w, h, fill in RECTS:
                if x <= (col + .5) * 64 / size < x + w and y <= (row + .5) * 64 / size < y + h:
                    color = fill
            pixels.extend(bytes.fromhex(color[1:]) + b'\xff')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(pixels), 9)) + chunk(b'IEND', b''))


def icon_ico():
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [icon_png(size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    entries = []
    for size, png in zip(sizes, images):
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(png), offset))
        offset += len(png)
    return struct.pack('<HHH', 0, 1, len(sizes)) + b''.join(entries) + b''.join(images)


def demo_data():
    """Fictional identifiers and neutral subjects, designed from scratch."""
    rooms = [[f'A-DEMO-{i}', f'Aula de ejemplo {i}', 'DEMO', 30 + i * 5, 24 + i * 4]
             for i in range(1, 7)]
    rooms += [[f'L-DEMO-{i}', f'Laboratorio de ejemplo {i}', 'DEMO', 24, 19] for i in range(1, 3)]
    subjects = ['Pensamiento lógico', 'Diseño de proyectos', 'Comunicación visual',
                'Modelos y patrones', 'Exploración de datos', 'Trabajo colaborativo',
                'Sistemas y procesos', 'Presentación de ideas', 'Taller de prototipos',
                'Proyecto integrador', 'Laboratorio de modelos', 'Laboratorio de prototipos']
    rows, config = [], []
    days = ['L', 'I', 'M', 'J', 'V', 'S']
    for index, subject in enumerate(subjects):
        code = f'DEM{101 + index}' + ('L' if index >= 10 else '')
        room = f'L-DEMO-{index - 9}' if index >= 10 else f'A-DEMO-{index % 6 + 1}'
        duration = 6 if index == 9 else (1.5 if index == 8 else 2)
        end = '1400' if duration == 6 else ('0930' if duration == 1.5 else '1000')
        for group in range(3):
            rows.append([code, f'{subject} (ejemplo)', 1, '0800-' + end, room, days[(index + group * 2) % 6]])
        config.append({'code': code, 'name': f'{subject} (ejemplo)', 'number_of_groups': 3,
                       'duration': duration, 'suggested_classroom': room})
    return {'Aulas': [['# DE AULA', 'DESCRIPCIÓN', 'CAMPUS', 'CAPACIDAD', 'CAPACIDAD 80%']] + rooms,
            'Cursos': [['Curso', 'Nombre de Curso', 'Cantidad de Grupos', 'Horas', 'Aula', 'Días']] + rows}, {'courses': config}


def generate(root=ROOT):
    root = Path(root)
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    (root / 'data/input').mkdir(parents=True, exist_ok=True)
    (root / 'assets/sorth.svg').write_bytes(icon_svg())
    (root / 'assets/sorth.ico').write_bytes(icon_ico())
    (root / 'schedule-board.png').write_bytes(icon_png(256))
    sheets, config = demo_data()
    for name, data in [('demo_source.json', sheets), ('courses_config.json', config)]:
        (root / 'data/input' / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=ROOT)
    generate(parser.parse_args().output_root)
