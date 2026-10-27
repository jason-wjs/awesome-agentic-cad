"""Tessellate the full and sectioned STEP parts for the teaser.

The STEP files remain the geometry source. Face boundaries are preserved so
curved surfaces shade smoothly without rounding machined edges.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import numpy as np
from build123d import import_step


def export(source: Path, output: Path):
    source = source.resolve()
    manifest_path = source / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    data = bytearray()
    hashes = {'manifest.json': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    cached = {}
    triangle_count = 0

    def tessellate(path: Path):
        nonlocal triangle_count
        relative = path.relative_to(source).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[relative] = digest
        if digest in cached:
            return cached[digest]
        vertices, triangles = import_step(path).tessellate(0.12, 0.24)
        positions = np.array([list(v) for v in vertices], dtype='<f4')
        indices = np.array(triangles, dtype='<u4').flatten()
        spec = {'position_offset': len(data), 'vertex_count': len(positions)}
        data.extend(positions.tobytes())
        spec.update(index_offset=len(data), index_count=len(indices))
        data.extend(indices.tobytes())
        triangle_count += len(triangles)
        cached[digest] = spec
        return spec

    for entry in manifest['parts']:
        entry['mesh'] = tessellate(source / 'parts' / (entry['name'] + '.step'))
        if entry.get('cutaway') and entry.get('presentation_step'):
            entry['cut_mesh'] = tessellate(source / entry['presentation_step'])
    manifest['mesh_file'] = output.with_suffix('.bin.gz').name
    manifest['source_sha256'] = hashes
    manifest['mesh_sha256'] = hashlib.sha256(data).hexdigest()
    manifest['tessellation'] = {'linear_tolerance_mm': 0.12, 'angular_tolerance_rad': 0.24,
                                'triangle_count': triangle_count, 'face_boundaries_preserved': True}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.bin.gz').write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    output.with_suffix('.json').write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
    print(json.dumps({'source': source.name, 'parts': len(manifest['parts']),
                      'triangles': triangle_count, 'bytes': len(data),
                      'compressed_bytes': output.with_suffix('.bin.gz').stat().st_size}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Output prefix without suffix')
    args = parser.parse_args()
    export(args.source, args.output)
