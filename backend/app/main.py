import random, math
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import volume_layout as vl

app = FastAPI(title="Medical Imaging Viewer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class VolumeRequest(BaseModel):
    preset: str = "brain"  # brain / chest / abdomen
    width: int = 64
    height: int = 64
    depth: int = 64


class ROIRequest(BaseModel):
    center: list = [32, 32, 32]
    radius: int = 10
    label: str = "lesion"


class WindowLevelRequest(BaseModel):
    window: float = 400.0
    level: float = 40.0
    preset: str = "brain"


WINDOW_PRESETS = {
    "lung":     {"window": 1500, "level": -600, "desc": "肺窗 (W1500/L-600)"},
    "mediastinum": {"window": 350, "level": 50, "desc": "纵隔窗 (W350/L50)"},
    "bone":     {"window": 2000, "level": 300, "desc": "骨窗 (W2000/L300)"},
    "brain":    {"window": 80, "level": 40, "desc": "脑窗 (W80/L40)"},
    "abdomen":  {"window": 400, "level": 40, "desc": "腹窗 (W400/L40)"},
}


def generate_volume(preset: str, w: int, h: int, d: int):
    """Generate synthetic CT-like volume.

    轴序口径来自 volume_layout：体数组形状 = (depth, height, width)，
    体素统一经 zi = vl.voxel_index(x, y, z) 写入，不再散落 [z, y, x] 下标。
    """
    np.random.seed(42)
    vol = np.zeros(vl.make_shape(width=w, height=h, depth=d), dtype=np.float32)

    center_x, center_y, center_z = w//2, h//2, d//2
    for z in range(d):
        for y in range(h):
            for x in range(w):
                # volume[z][y][x] —— 全文件唯一的体素下标口径
                zi = vl.voxel_index(x, y, z)
                # Head-like shape
                rx = (x - center_x - 5) / (w * 0.4)
                ry = (y - center_y) / (h * 0.45)
                rz = (z - center_z + 3) / (d * 0.4)
                dist = math.sqrt(rx**2 + ry**2 + rz**2)

                if preset == "brain":
                    if dist < 0.85:
                        # Brain tissue
                        base = 35
                        # Sulci pattern
                        noise = (np.sin(x * 0.4) * np.cos(y * 0.3) + np.sin(z * 0.35)) * 8
                        # Ventricles (CSF)
                        vent_dist = math.sqrt(((x-center_x+2)/(w*0.15))**2 + ((y-center_y)/(h*0.12))**2 + ((z-center_z)/(d*0.1))**2)
                        if vent_dist < 0.6:
                            base = 10 + noise * 0.3
                        # Skull
                        if dist > 0.7 and dist < 0.85:
                            base = 200 + random.uniform(-20, 20)
                        vol[zi] = base + noise
                    elif dist < 0.9:
                        vol[zi] = 100  # Scalp
                elif preset == "chest":
                    # Body oval
                    bx = (x - center_x) / (w * 0.35)
                    by = (y - center_y) / (h * 0.4)
                    body = math.sqrt(bx**2 + by**2)
                    if body < 1.0:
                        # Lungs (dark)
                        lung_dist1 = math.sqrt(((x-center_x+8)/(w*0.12))**2 + ((y-center_y)/(h*0.13))**2)
                        lung_dist2 = math.sqrt(((x-center_x-8)/(w*0.12))**2 + ((y-center_y)/(h*0.13))**2)
                        if lung_dist1 < 0.7 or lung_dist2 < 0.7:
                            vol[zi] = -650 + np.sin(z*0.3)*30
                        else:
                            vol[zi] = 30 + np.random.uniform(-5, 5)
                        # Spine
                        if abs(x - center_x) < 3 and abs(y - center_y + 8) < 4:
                            vol[zi] = 250
                    vol[zi] += np.random.uniform(-3, 3)
                elif preset == "abdomen":
                    bx = (x - center_x) / (w * 0.33)
                    by = (y - center_y) / (h * 0.4)
                    body = math.sqrt(bx**2 + by**2)
                    if body < 1.0:
                        base = 35
                        # Liver (right upper)
                        lv = math.sqrt(((x-center_x-6)/(w*0.08))**2 + ((y-center_y+4)/(h*0.07))**2)
                        if lv < 0.6:
                            base = 55 + np.random.uniform(-5, 5)
                        # Kidneys
                        kd1 = math.sqrt(((x-center_x-5)/(w*0.04))**2 + ((y-center_y-5)/(h*0.04))**2)
                        kd2 = math.sqrt(((x-center_x+5)/(w*0.04))**2 + ((y-center_y-5)/(h*0.04))**2)
                        if kd1 < 0.4 or kd2 < 0.4:
                            base = 45
                        # Spine
                        if abs(x - center_x) < 3 and abs(y - center_y + 7) < 4:
                            base = 250 + np.random.uniform(-10, 10)
                        vol[zi] = base + np.random.uniform(-9, 9)

    return vol.tolist()


@app.post("/api/volume")
def get_volume(req: VolumeRequest):
    vol = generate_volume(req.preset, req.width, req.height, req.depth)

    # MPR 中切片：切面行列口径全部由 volume_layout.MPR_PLANES 注册表给出
    mpr = vl.extract_mpr_slices(vol, req.width, req.height, req.depth)

    # Return: 3D volume + 3 MPR slices
    return {
        "volume": vol,
        "dimensions": vl.dims_dhw(req.width, req.height, req.depth),
        "mpr": mpr,
        "preset": req.preset,
        "windowPresets": WINDOW_PRESETS
    }


class ROIAnalyzeRequest(BaseModel):
    volume: list
    rois: list = []


@app.post("/api/roi")
def analyze_roi(req: ROIAnalyzeRequest):
    results = []
    for roi in req.rois:
        center = roi.get("center", [32, 32, 32])
        radius = roi.get("radius", 8)
        label = roi.get("label", "roi")

        # Extract voxels within sphere
        voxels = []
        try:
            arr3d = np.array(req.volume)
            # 形状按 volume_layout 的 (depth, height, width) 轴序解析
            sizes = dict(zip(vl.AXES_DHW, arr3d.shape))
            c = vl.roi_center_xyz(center)  # center 列表 [x, y, z]
            spans = {
                axis: range(max(0, c[axis] - radius),
                            min(sizes[axis], c[axis] + radius + 1))
                for axis in vl.AXES_DHW
            }
            for z in spans[vl.AXIS_Z]:
                for y in spans[vl.AXIS_Y]:
                    for x in spans[vl.AXIS_X]:
                        if math.sqrt((x-c[vl.AXIS_X])**2 + (y-c[vl.AXIS_Y])**2 + (z-c[vl.AXIS_Z])**2) <= radius:
                            voxels.append(float(arr3d[vl.voxel_index(x, y, z)]))
        except:
            voxels = []

        if voxels:
            arr = np.array(voxels)
            results.append({
                "label": label,
                "center": center,
                "radius": radius,
                "mean": round(float(np.mean(arr)), 2),
                "std": round(float(np.std(arr)), 2),
                "min": round(float(np.min(arr)), 2),
                "max": round(float(np.max(arr)), 2),
                "voxelCount": len(voxels),
                "histogram": np.histogram(arr, bins=10, range=(float(np.min(arr)), float(np.max(arr))))[0].tolist()
            })

    return {"rois": results}


@app.get("/api/windows")
def get_windows():
    return {"presets": WINDOW_PRESETS}