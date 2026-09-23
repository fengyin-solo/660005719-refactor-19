/**
 * 体数据下标口径 —— 前端唯一规则来源（single source of truth）
 *
 * 与后端 backend/app/volume_layout.py 保持镜像一致；修改轴序约定时两端同步。
 * 点云取样、MPR 切面、ROI 测量等所有呈现方式都必须经本模块取体素/查轴长，
 * 不再各自硬编码 volume[z][y][x] 或 dimensions 下标。
 *
 * 新增一种呈现方式（例如新的切面）时，只需在 MPR_PLANES 注册表里扩展一项。
 */

/** 体素嵌套下标：volume[z][y][x] */
export const AXIS_Z = 'z' // 深度轴（轴位）
export const AXIS_Y = 'y' // 高度轴（冠状位）
export const AXIS_X = 'x' // 宽度轴（矢状位）
export type Axis = typeof AXIS_X | typeof AXIS_Y | typeof AXIS_Z

/** volume / dimensions 中三个下标的固定轴序 */
export const AXES_DHW: Axis[] = [AXIS_Z, AXIS_Y, AXIS_X]

/** 对外 dimensions 字段顺序：[depth, height, width] */
export type Dimensions = [depth: number, height: number, width: number]

/** ROI center 列表的轴序：center[0]=x, center[1]=y, center[2]=z */
export const ROI_CENTER_XYZ: Axis[] = [AXIS_X, AXIS_Y, AXIS_Z]

/** 任意轴组合的坐标/轴长表 */
export type Coord = Record<Axis, number>
export type AxisSizes = Record<Axis, number>

/** 把 [depth, height, width] 解析为按轴名查询的轴长表 */
export function axisSizes(dimensions: Dimensions): AxisSizes {
  return {
    [AXIS_Z]: dimensions[0],
    [AXIS_Y]: dimensions[1],
    [AXIS_X]: dimensions[2],
  }
}

/** volume[z][y][x] —— 全前端唯一的体素取值口径 */
export function getVoxel(volume: number[][][], c: Coord): number {
  return volume[c[AXIS_Z]][c[AXIS_Y]][c[AXIS_X]]
}

/** MPR 切面注册表：新增切面只需在此扩展一项
 * fixedAxis —— 切面法线轴（slider 沿该轴扫，中切片取该轴 size//2）
 * rowAxis   —— 二维数组的行轴（canvas y）
 * colAxis   —— 二维数组的列轴（canvas x）
 */
export interface PlaneSpec {
  fixedAxis: Axis
  rowAxis: Axis
  colAxis: Axis
}

export const MPR_PLANES: Record<string, PlaneSpec> = {
  axial: { fixedAxis: AXIS_Z, rowAxis: AXIS_Y, colAxis: AXIS_X },
  coronal: { fixedAxis: AXIS_Y, rowAxis: AXIS_Z, colAxis: AXIS_X },
  sagittal: { fixedAxis: AXIS_X, rowAxis: AXIS_Z, colAxis: AXIS_Y },
}

/** 从体数据实时抽取指定切面，返回 list[row][col]（口径由注册表给出） */
export function extractSlice(
  volume: number[][][],
  sizes: AxisSizes,
  plane: PlaneSpec,
  index: number,
): number[][] {
  const { fixedAxis, rowAxis, colAxis } = plane
  const data: number[][] = []
  for (let row = 0; row < sizes[rowAxis]; row++) {
    const line: number[] = []
    for (let col = 0; col < sizes[colAxis]; col++) {
      line.push(
        getVoxel(volume, {
          [fixedAxis]: index,
          [rowAxis]: row,
          [colAxis]: col,
        } as Coord),
      )
    }
    data.push(line)
  }
  return data
}

/** 各切面中切片（固定轴中点），与后端 extract_mpr_slices 对应 */
export function extractMidSlices(
  volume: number[][][],
  dimensions: Dimensions,
): Record<string, number[][]> {
  const sizes = axisSizes(dimensions)
  return Object.fromEntries(
    Object.entries(MPR_PLANES).map(([name, plane]) => [
      name,
      extractSlice(volume, sizes, plane, Math.floor(sizes[plane.fixedAxis] / 2)),
    ]),
  )
}

/** 某切面 slider 的最大下标（= 固定轴长度 - 1） */
export function planeMaxSlice(dimensions: Dimensions, planeName: string): number {
  const sizes = axisSizes(dimensions)
  return sizes[MPR_PLANES[planeName].fixedAxis] - 1
}

/** ROI 中心第 i 个输入框对应的轴及其合法最大下标 */
export function roiAxisAt(dimensions: Dimensions | null, i: number): { axis: Axis; max: number } {
  const axis = ROI_CENTER_XYZ[i]
  const sizes = dimensions ? axisSizes(dimensions) : { [AXIS_X]: 64, [AXIS_Y]: 64, [AXIS_Z]: 64 }
  return { axis, max: sizes[axis] - 1 }
}
