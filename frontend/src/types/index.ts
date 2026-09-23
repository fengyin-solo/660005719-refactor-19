import type { Dimensions } from '@/lib/volumeLayout'

export interface WindowPreset { window: number; level: number; desc: string }
export interface VolumeData {
  volume: number[][][]
  /** 轴序口径见 lib/volumeLayout：[depth, height, width] = [z, y, x] */
  dimensions: Dimensions
  mpr: { axial: number[][]; coronal: number[][]; sagittal: number[][] }
  preset: string
  windowPresets: Record<string, WindowPreset>
}

export interface ROIResult {
  label: string; center: number[]; radius: number
  mean: number; std: number; min: number; max: number; voxelCount: number
  histogram: number[]
}