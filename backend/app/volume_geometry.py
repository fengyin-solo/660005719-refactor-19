import math
from dataclasses import dataclass
from typing import Iterator, List, Union

import numpy as np


@dataclass(frozen=True)
class Axis:
    key: str
    label: str
    dimension_index: int


@dataclass(frozen=True)
class PlaneView:
    name: str
    title: str
    fixed_axis: str
    row_axis: str
    column_axis: str


# 体数据嵌套顺序 / numpy shape 统一为：深度(z)、高度(y)、宽度(x)。
AXES = (
    Axis("z", "深度", 0),
    Axis("y", "高度", 1),
    Axis("x", "宽度", 2),
)
AXIS_BY_KEY = {axis.key: axis for axis in AXES}

# ROI 中心点的对外输入顺序：x（宽）、y（高）、z（深）。
CENTER_ORDER = ("x", "y", "z")

# 新增切面时只需在这里补充 fixed/row/column 的轴映射。
PLANE_VIEWS = (
    PlaneView("axial", "横断面 (轴位)", fixed_axis="z", row_axis="y", column_axis="x"),
    PlaneView("coronal", "冠状面", fixed_axis="y", row_axis="z", column_axis="x"),
    PlaneView("sagittal", "矢状面", fixed_axis="x", row_axis="z", column_axis="y"),
)


def coordinate_system() -> dict:
    return {
        "axes": [
            {"key": axis.key, "label": axis.label, "dimensionIndex": axis.dimension_index}
            for axis in AXES
        ],
        "centerOrder": list(CENTER_ORDER),
        "planes": [
            {
                "name": view.name,
                "title": view.title,
                "fixedAxis": view.fixed_axis,
                "rowAxis": view.row_axis,
                "columnAxis": view.column_axis,
            }
            for view in PLANE_VIEWS
        ],
    }


def volume_shape(width: int, height: int, depth: int) -> tuple:
    return tuple(
        {"z": depth, "y": height, "x": width}[axis.key]
        for axis in AXES
    )


def axis_size(shape: tuple, axis_key: str) -> int:
    return shape[AXIS_BY_KEY[axis_key].dimension_index]


def extract_slice(volume: np.ndarray, view: PlaneView, index: int) -> np.ndarray:
    selector: List[Union[slice, int]] = [slice(None)] * len(AXES)
    selector[AXIS_BY_KEY[view.fixed_axis].dimension_index] = index
    plane = volume[tuple(selector)]

    remaining_axes = [axis.key for axis in AXES if axis.key != view.fixed_axis]
    wanted_axes = [view.row_axis, view.column_axis]
    if remaining_axes != wanted_axes:
        plane = np.transpose(
            plane,
            [remaining_axes.index(axis_key) for axis_key in wanted_axes],
        )
    return plane


def mpr_slices(volume: np.ndarray) -> dict:
    return {
        view.name: extract_slice(
            volume,
            view,
            axis_size(volume.shape, view.fixed_axis) // 2,
        ).tolist()
        for view in PLANE_VIEWS
    }


def iter_sphere_voxels(
    volume: np.ndarray,
    center_xyz: List[float],
    radius: int,
) -> Iterator[float]:
    center = {
        axis.key: int(center_xyz[CENTER_ORDER.index(axis.key)])
        for axis in AXES
    }
    bounds = {}
    for axis in AXES:
        position = center[axis.key]
        bounds[axis.key] = (
            max(0, position - radius),
            min(axis_size(volume.shape, axis.key), position + radius + 1),
        )

    def visit(axis_index: int, indices: dict) -> Iterator[float]:
        if axis_index == len(AXES):
            distance = math.sqrt(
                sum((indices[key] - center[key]) ** 2 for key in CENTER_ORDER)
            )
            if distance <= radius:
                value = volume[tuple(indices[axis.key] for axis in AXES)]
                yield float(value)
            return

        axis = AXES[axis_index]
        start, stop = bounds[axis.key]
        for index in range(start, stop):
            indices[axis.key] = index
            yield from visit(axis_index + 1, indices)

    yield from visit(0, {})
