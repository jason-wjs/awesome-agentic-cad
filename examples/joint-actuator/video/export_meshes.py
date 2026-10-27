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
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.StdPrs import StdPrs_ToolTriangulatedShape
from OCP.TopLoc import TopLoc_Location
from OCP.TopAbs import TopAbs_Orientation


def cad_tessellation(shape, linear_tolerance=0.045, angular_tolerance=0.12):
    """Use absolute millimetre deflection and analytic surface normals."""
    BRepMesh_IncrementalMesh(shape.wrapped, linear_tolerance, False, angular_tolerance, True)
    positions, normals, indices = [], [], []
    for face in shape.faces():
        location = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face.wrapped, location)
        transform = location.Transformation()
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        StdPrs_ToolTriangulatedShape.ComputeNormals_s(face.wrapped, tri)
        offset = len(positions)
        for i in range(1, tri.NbNodes()+1):
            point = tri.Node(i).Transformed(transform)
            normal = tri.Normal(i).Transformed(transform)
            if reverse:
                normal.Reverse()
            positions.append((point.X(), point.Y(), point.Z()))
            normals.append((normal.X(), normal.Y(), normal.Z()))
        for triangle in tri.Triangles():
            a, b, c = (triangle.Value(i)+offset-1 for i in (1, 2, 3))
            indices.append((a, c, b) if reverse else (a, b, c))
    return (np.asarray(positions, dtype='<f4'), np.asarray(normals, dtype='<f4'),
            np.asarray(indices, dtype='<u4').flatten())


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
        angular_tolerance = 0.24 if path.name.startswith('winding_') else 0.12
        positions, normals, indices = cad_tessellation(import_step(path), angular_tolerance=angular_tolerance)
        spec = {'position_offset': len(data), 'vertex_count': len(positions)}
        data.extend(positions.tobytes())
        spec.update(normal_offset=len(data))
        data.extend(normals.tobytes())
        spec.update(index_offset=len(data), index_count=len(indices))
        data.extend(indices.tobytes())
        triangle_count += len(indices)//3
        cached[digest] = spec
        return spec

    for entry in manifest['parts']:
        entry['mesh'] = tessellate(source / 'parts' / (entry['name'] + '.step'))
        if entry.get('cutaway') and entry.get('presentation_step'):
            entry['cut_mesh'] = tessellate(source / entry['presentation_step'])
    manifest['mesh_file'] = output.with_suffix('.bin.gz').name
    manifest['source_sha256'] = hashes
    manifest['mesh_sha256'] = hashlib.sha256(data).hexdigest()
    manifest['tessellation'] = {'linear_tolerance_mm': 0.045, 'angular_tolerance_rad': {'windings': 0.24, 'other': 0.12}, 'relative_deflection': False, 'normals': 'analytic CAD surface normals',
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
