<template>
  <canvas ref="cvs" width="160" height="160" class="mpr-canvas"></canvas>
  <input type="range" class="slider" :min="0" :max="maxSlice" v-model="slice" @input="draw"/>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useImagingStore } from '../store/imaging'
import { planeMaxSlice, type Dimensions } from '../lib/volumeLayout'
const props = defineProps<{ plane: string }>()
const store = useImagingStore()
const cvs = ref<HTMLCanvasElement>()
const slice = ref(32)

const FALLBACK_DIMS: Dimensions = [64, 64, 64]

// slider 上限 = 该切面固定轴长度 - 1（口径来自 MPR_PLANES 注册表）
const maxSlice = computed(() =>
  planeMaxSlice(store.volumeData?.dimensions ?? FALLBACK_DIMS, props.plane)
)

function draw() {
  const c = cvs.value!; const ctx = c.getContext('2d')!; const W = c.width, H = c.height
  ctx.fillStyle = '#0d1117'; ctx.fillRect(0, 0, W, H)

  const vd = store.volumeData
  if (!vd) return

  // 后端按 MPR_PLANES 注册表同名输出中切片，此处按 plane 名直接取用
  let sliceData: number[][] | null = (vd.mpr as Record<string, number[][]>)[props.plane] ?? null

  if (!sliceData || !sliceData.length) return

  const wl = store.windowVal, ww = store.levelVal
  const lower = wl - ww / 2, upper = wl + ww / 2

  const rows = sliceData.length, cols = sliceData[0].length
  const cellW = W / cols, cellH = H / rows

  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      let val = sliceData[y][x]
      let t = (val - lower) / (upper - lower)
      t = Math.max(0, Math.min(1, t))
      const gray = Math.floor(t * 255)
      ctx.fillStyle = `rgb(${gray},${gray},${gray})`
      ctx.fillRect(x * cellW, y * cellH, cellW + 0.5, cellH + 0.5)
    }
  }
}

watch(() => store.volumeData, draw, { deep: true })
watch(() => [store.windowVal, store.levelVal], draw)
onMounted(draw)
</script>

<style scoped>
.mpr-canvas { display: block; width: 100%; aspect-ratio: 1; border-radius: 4px; }
.slider { width: 100%; margin: 4px 0; accent-color: #58a6ff; height: 4px; }
</style>