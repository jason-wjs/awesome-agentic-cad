"""Export per-face STEP tessellation for the deterministic Three.js film.

Vertices are not welded across CAD faces: computed vertex normals remain smooth
on a cylinder and retain sharp edges between planar faces.
"""
from pathlib import Path
import argparse
import hashlib
import gzip
import json
import numpy as np
from build123d import import_step


def export(source, output):
    manifest_path = source / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    data = bytearray()
    hashes = {'manifest.json': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    triangle_count = 0
    for entry in manifest['parts']:
        path = source / 'parts' / (entry['name'] + '.step')
        hashes['parts/' + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        vertices, triangles = import_step(path).tessellate(0.06, 0.14)
        positions = np.array([list(v) for v in vertices], dtype='<f4')
        indices = np.array(triangles, dtype='<u4').flatten()
        entry['mesh'] = {'position_offset': len(data), 'vertex_count': len(positions)}
        data.extend(positions.tobytes())
        entry['mesh'].update(index_offset=len(data), index_count=len(indices))
        data.extend(indices.tobytes())
        triangle_count += len(triangles)
    manifest['mesh_file'] = output.name + '.bin.gz'
    manifest['source_sha256'] = hashes
    manifest['mesh_sha256'] = hashlib.sha256(data).hexdigest()
    manifest['tessellation'] = {'linear_tolerance_mm': 0.06, 'angular_tolerance_rad': 0.14,
                                'triangle_count': triangle_count, 'face_boundaries_preserved': True}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.bin.gz').write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    output.with_suffix('.json').write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
    print(f'{source.name}: {len(manifest["parts"])} parts, {triangle_count} triangles, {len(data)} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Output prefix without suffix')
    args = parser.parse_args()
    export(args.source, args.output)
