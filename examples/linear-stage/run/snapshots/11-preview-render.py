"""Render named STEP parts as assemblies, exploded views, and travel comparisons."""
from pathlib import Path
import argparse
import json
import os
import tempfile
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'awesome-cad-mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
import numpy as np
from build123d import import_step

HERE=Path(__file__).parent
ROOT=HERE.parents[1]
INK='#18354a'
MUTED='#526c7d'
TEAL='#197d86'
BG='#edf3f6'


def load_meshes(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    meshes=[]
    for item in manifest['parts']:
        shape=import_step(str(folder/'parts'/f"{item['name']}.step"))
        vertices,triangles=shape.tessellate(.15)
        meshes.append((item['name'],np.array([list(v) for v in vertices]),np.array(triangles),item['color_rgba'][:3]))
    return manifest,meshes


def explode(name):
    if name=='platform' or name.startswith(('platform_bolt','nut_bolt')): return (0,0,112)
    if name.startswith(('guide_housing','nut_holder')): return (0,0,72)
    if name.startswith('guide_bushing'): return (0,0,45)
    if name=='drive_nut': return (-12,0,39)
    if name.startswith('guide_rod'): return (0,0,24)
    if name=='lead_screw': return (0,0,24)
    if name.startswith('screw_bearing'): return ((-20 if name.endswith('left') else 20),0,24)
    if name.startswith('end_support'): return ((-20 if name.endswith('left') else 20),0,0)
    if name.startswith('support_bolt'): return ((-20 if 'left' in name else 20),0,10)
    if name.startswith(('motor','mount_bolt')): return (50,0,10)
    if name=='coupling': return (25,0,24)
    return (0,0,0)


def raster(meshes, camera=(.52,-.72,.46), explode_view=False, span=330, center=(30,0,30), width=1400, height=850):
    """Orthographic z-buffer from actual B-rep tessellations; no illustrative geometry."""
    camera=np.array(camera,dtype=float);camera/=np.linalg.norm(camera)
    right=np.cross([0,0,1],camera);right/=np.linalg.norm(right)
    up=np.cross(camera,right)
    basis=np.stack([right,up,camera],axis=1)
    depth=np.full((height,width),-np.inf)
    rgba=np.ones((height,width,4));rgba[:,:,3]=0
    light=np.array([-.35,-.5,.79]);light/=np.linalg.norm(light)
    scale=width/span
    for name,vs,ts,color in meshes:
        vertices=vs + np.array(explode(name) if explode_view else (0,0,0))
        projected=(vertices-np.array(center))@basis
        pixels=projected.copy()
        pixels[:,0]=width/2+projected[:,0]*scale
        pixels[:,1]=height/2-projected[:,1]*scale
        for ids in ts:
            points=pixels[ids];face=vertices[ids]
            lo=np.maximum(np.floor(points[:,:2].min(axis=0)).astype(int),[0,0])
            hi=np.minimum(np.ceil(points[:,:2].max(axis=0)).astype(int),[width-1,height-1])
            if np.any(lo>hi):continue
            xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
            a,b,c=points
            denom=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denom)<1e-10:continue
            w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denom
            w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denom
            w2=1-w0-w1
            z=w0*a[2]+w1*b[2]+w2*c[2]
            patch=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            mask=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)&(z>patch)
            normal=np.cross(face[1]-face[0],face[2]-face[0]);normal/=max(np.linalg.norm(normal),1e-12)
            if normal@camera<0:normal=-normal
            shade=.60+.40*max(0,normal@light)
            patch[mask]=z[mask]
            tile=rgba[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            tile[mask,:3]=np.array(color)*shade;tile[mask,3]=1
    return rgba


def show(fig,rect,img):
    ax=fig.add_axes(rect);ax.imshow(img,interpolation='lanczos');ax.axis('off');return ax


def set_font(zh,font):
    if zh:
        if font:
            font_manager.fontManager.addfont(font)
            name=font_manager.FontProperties(fname=font).get_name()
        else:
            names={f.name for f in font_manager.fontManager.ttflist}
            name=next((n for n in ('PingFang SC','Noto Sans CJK SC') if n in names),'DejaVu Sans')
        plt.rcParams['font.family']=[name,'DejaVu Sans']
    else:plt.rcParams['font.family']='DejaVu Sans'


def comparison(fig,rect,images,zh=False):
    x,y,w,h=rect
    for i,(travel,img) in enumerate(zip((80,120),images)):
        bottom=y+h*(.52 if i==0 else 0)
        ax=show(fig,[x,bottom,w,h*.48],img)
        # Both renders share the same camera, span, center and pixel dimensions.
        ax.text(.015,.86,f'{travel} mm',transform=ax.transAxes,fontsize=11,color=TEAL,fontweight='bold')
        left=.5-1400/330*travel/2/1400
        right=.5+1400/330*travel/2/1400
        ax.annotate('',xy=(right,.17),xytext=(left,.17),xycoords='axes fraction',
                    arrowprops=dict(arrowstyle='<->',lw=1.2,color=TEAL))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font')
    args=parser.parse_args()
    original,mesh80=load_meshes(HERE/'generated/80')
    revised,mesh120=load_meshes(HERE/'generated/120')
    assembly_img=raster(mesh120,span=350,center=(30,0,27))
    exploded_img=raster(mesh120,explode_view=True,span=420,center=(40,0,70),height=1100)
    # Side view: X points right. Center x=0 makes arrows match carriage travel.
    side=[raster(m,camera=(0,-1,.48),span=330,center=(0,0,21),height=450) for m in (mesh80,mesh120)]
    out=HERE/'generated'
    assets=ROOT/'assets'
    for zh in (False,True):
        set_font(zh,args.font)
        fig=plt.figure(figsize=(15,6.25),dpi=160,facecolor=BG)
        for x in (.014,.343,.672):
            fig.add_artist(FancyBboxPatch((x,.025),.314,.95,boxstyle='round,pad=0.006,rounding_size=.018',
                           facecolor='white',edgecolor='#d8e3ea',lw=.8,zorder=0))
        xs=(.035,.364,.693)
        headers=['01 / 建模','02 / 拆解装配','03 / 改参与检查'] if zh else ['01 / BUILD','02 / INSPECT','03 / REVISE & CHECK']
        titles=['丝杆驱动直线滑台','零件与装配关系','行程 80 → 120 mm'] if zh else ['Screw-driven linear stage','Inside the assembly','Travel 80 → 120 mm']
        subs=['双导向杆 · 移动平台 · 电机','独立零件 STEP · 分色爆炸图','同一比例 · 安装接口保持不变'] if zh else ['Twin guides · carriage · motor','Named STEP parts · exploded view','Same scale · mounting interfaces retained']
        for x,h,t,s in zip(xs,headers,titles,subs):
            fig.text(x,.91,h,fontsize=10,color=TEAL,fontweight='bold')
            fig.text(x,.835,t,fontsize=15.3,color=INK,fontweight='bold')
            fig.text(x,.777,s,fontsize=9.5,color=MUTED)
        show(fig,[.024,.225,.294,.52],assembly_img)
        show(fig,[.353,.205,.294,.55],exploded_img)
        comparison(fig,[.681,.225,.30,.52],side,zh)
        notes=[('真实 STEP 几何','Codex + build123d · 可复现代码与日志'),('36 个具名零件','平台、导向、传动及紧固件分开导出'),('两种行程均通过检查','每种 9 个位置 · 干涉与接口检查')] if zh else [('Actual STEP geometry','Codex + build123d · source & run logs'),('36 named components','Platform, guides, drive and fasteners'),('Both travel variants checked','9 positions each · interference & interfaces')]
        for x,(a,b) in zip(xs,notes):
            fig.text(x,.16,a,fontsize=11.4,color=INK,fontweight='bold')
            fig.text(x,.095,b,fontsize=9,color=MUTED)
        fig.savefig(assets/('cad-workflow.zh-CN.png' if zh else 'cad-workflow.png'))
        plt.close(fig)
    set_font(False,None)
    for title,img,name in [('120 mm travel / assembled',assembly_img,'assembly'),('Exploded assembly / 36 components',exploded_img,'exploded')]:
        fig=plt.figure(figsize=(12,8),dpi=160,facecolor='white')
        fig.text(.06,.92,title,fontsize=23,color=INK,fontweight='bold')
        show(fig,[.03,.1,.94,.78],img)
        fig.savefig(out/f'{name}.png');plt.close(fig)
    fig=plt.figure(figsize=(12,8),dpi=160,facecolor='white')
    fig.text(.06,.94,'80 → 120 mm travel',fontsize=23,color=INK,fontweight='bold')
    fig.text(.06,.89,'Same scale. Platform and motor interfaces retained.',fontsize=13,color=MUTED)
    comparison(fig,[.05,.08,.90,.76],side)
    fig.savefig(out/'travel-comparison.png');plt.close(fig)
    print('Rendered bilingual README images and three detail views from exported STEP parts.')


if __name__=='__main__':main()
