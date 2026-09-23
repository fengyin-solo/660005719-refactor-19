export type AxisKey = 'z' | 'y' | 'x'

export interface AxisDefinition {
  key: AxisKey
  label: string
  dimensionIndex: number
}

export interface PlaneDefinition {
  name: string
  title: string
  fixedAxis: AxisKey
  rowAxis: AxisKey
  columnAxis: AxisKey
}

export interface CoordinateSystem {
  axes: AxisDefinition[]
  centerOrder: AxisKey[]
  planes: PlaneDefinition[]
}

export interface WindowPreset { window: number; level: number; desc: string }
export interface VolumeData {
  volume: number[][][]
  dimensions: [number, number, number]
  mpr: Record<string, number[][]>
  coordinateSystem: CoordinateSystem
  preset: string
  windowPresets: Record<string, WindowPreset>
}

export interface ROIResult {
  label: string; center: number[]; radius: number
  mean: number; std: number; min: number; max: number; voxelCount: number
  histogram: number[]
}

export function axisDefinition(
  coordinateSystem: CoordinateSystem,
  axis: AxisKey
): AxisDefinition {
  return coordinateSystem.axes.find(item => item.key === axis)!
}

export function axisSize(
  dimensions: readonly number[],
  coordinateSystem: CoordinateSystem,
  axis: AxisKey
): number {
  return dimensions[axisDefinition(coordinateSystem, axis).dimensionIndex]
}

export function voxelAt(
  volume: number[][][] | undefined,
  dimensions: readonly number[],
  coordinateSystem: CoordinateSystem,
  position: Record<AxisKey, number>
): number | undefined {
  if (!volume) return undefined
  const indexByAxis = coordinateSystem.axes.map(({ key }) => position[key])
  if (indexByAxis.some((index, axisIndex) => index < 0 || index >= dimensions[axisIndex])) {
    return undefined
  }

  const [first, second, third] = indexByAxis
  return volume[first]?.[second]?.[third]
}
