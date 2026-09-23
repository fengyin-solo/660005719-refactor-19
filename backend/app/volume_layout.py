"""体数据下标口径 —— 全局唯一规则来源（single source of truth）

体数据各处（生成、点云取样、MPR 切面、ROI 测量）都必须经由本模块访问，
不再各自硬编码 [z][y][x] / dimensions 下标 / 切面行列顺序。

需要新增一种呈现方式（例如新的切面）时，只需在 MPR_PLANES 注册表里扩展一项。

体数据约定（与前端 src/lib/volumeLayout.ts 保持镜像一致）：
  volume[z][y][x]
      z —— 深度轴（轴位/横断面号），对应 dimensions[0]
      y —— 高度轴（冠状面号），对应 dimensions[1]
      x —— 宽度轴（矢状面号），对应 dimensions[2]
  dimensions = [depth, height, width]（见 DIMS_DHW / AXES_DHW）
  ROI 中心坐标按世界轴序 center[x, y, z]（见 ROI_CENTER_XYZ）
"""

# 体素嵌套下标：volume[z][y][x]
AXIS_Z = 'z'  # 深度轴（轴位）
AXIS_Y = 'y'  # 高度轴（冠状位）
AXIS_X = 'x'  # 宽度轴（矢状位）

# volume / dimensions 中三个下标的固定轴序
AXES_DHW = (AXIS_Z, AXIS_Y, AXIS_X)

# ROI center 列表的轴序：center[0]=x, center[1]=y, center[2]=z
ROI_CENTER_XYZ = (AXIS_X, AXIS_Y, AXIS_Z)


def make_shape(width, height, depth):
    """numpy 体数组形状，按 AXES_DHW = (z, y, x) 排列。"""
    return (depth, height, width)


def axis_sizes(width, height, depth):
    """{轴名: 该轴体素数}，供按轴查询，避免手写 z/y/x 下标。"""
    return {AXIS_X: width, AXIS_Y: height, AXIS_Z: depth}


def dims_dhw(width, height, depth):
    """对外 dimensions 字段：[depth, height, width]。"""
    return [depth, height, width]


def get_voxel(volume, coord):
    """按 {x,y,z} 坐标取体素：volume[z][y][x]。"""
    return volume[coord[AXIS_Z]][coord[AXIS_Y]][coord[AXIS_X]]


def voxel_index(x, y, z):
    """体数组下标元组 (z, y, x)，对应 make_shape 的 (depth, height, width)。"""
    return (z, y, x)


def extract_slice(volume, sizes, plane, index):
    """从体数据抽取指定切面的二维数组（纯 Python，行/列口径由注册表给出）。

    返回 list[row][col]，其中
      行轴 = plane['rowAxis']，沿 0..size[rowAxis]-1
      列轴 = plane['colAxis']，沿 0..size[colAxis]-1
      固定轴 = plane['fixedAxis']，取 index
    """
    fixed_axis = plane['fixedAxis']
    row_axis, col_axis = plane['rowAxis'], plane['colAxis']
    data = []
    for row in range(sizes[row_axis]):
        line = []
        for col in range(sizes[col_axis]):
            coord = {fixed_axis: index, row_axis: row, col_axis: col}
            line.append(get_voxel(volume, coord))
        data.append(line)
    return data


# MPR 切面注册表：新增切面只需在此扩展一项
# fixedAxis —— 切面法线轴（slider 沿该轴扫，中切片取该轴 size//2）
# rowAxis   —— 输出二维数组的行轴（canvas y）
# colAxis   —— 输出二维数组的列轴（canvas x）
MPR_PLANES = {
    # volume[midZ] 原样即为 [y][x]
    'axial':    {'fixedAxis': AXIS_Z, 'rowAxis': AXIS_Y, 'colAxis': AXIS_X},
    # 行=z, 列=x，固定 y
    'coronal':  {'fixedAxis': AXIS_Y, 'rowAxis': AXIS_Z, 'colAxis': AXIS_X},
    # 行=z, 列=y，固定 x
    'sagittal': {'fixedAxis': AXIS_X, 'rowAxis': AXIS_Z, 'colAxis': AXIS_Y},
}


def extract_mpr_slices(volume, width, height, depth):
    """按注册表生成全部 MPR 中切片（各取固定轴中点）。"""
    sizes = axis_sizes(width, height, depth)
    return {
        name: extract_slice(volume, sizes, plane, sizes[plane['fixedAxis']] // 2)
        for name, plane in MPR_PLANES.items()
    }


def roi_center_xyz(center):
    """把 ROI 中心列表 [x, y, z] 解析为 {x,y,z} 坐标。"""
    return {axis: center[i] for i, axis in enumerate(ROI_CENTER_XYZ)}
