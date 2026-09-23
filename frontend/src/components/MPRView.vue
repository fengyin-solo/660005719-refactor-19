<template>
  <canvas ref="cvs" width="160" height="160" class="mpr-canvas"></canvas>
  <input type="range" class="slider" :min="0" :max="maxSlice" v-model="slice" @input="draw"/>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useImagingStore } from '../store/imaging'
import {
  axisSize,
  type PlaneDefinition,
} from '../volumeGeometry'

const props = defineProps<{ plane: PlaneDefinition }>()
const store = useImagingStore()
const cvs = ref<HTMLCanvasElement>()
const slice = ref(0)

const maxSlice = computed(() => {
  const vd = store.volumeData
  if (!vd) return 0
  return axisSize(vd.dimensions, vd.coordinateSystem, props.plane.fixedAxis) - 1
})

watch(
  () => store.volumeData,
  () => {
    slice.value = Math.floor((maxSlice.value + 1) / 2)
    draw()
  },
  { deep: true }
)

function draw() {
  const c = cvs.value!; const ctx = c.getContext('2d')!; const W = c.width, H = c.height
  ctx.fillStyle = '#0d1117'; ctx.fillRect(0, 0, W, H)

  const vd = store.volumeData
  if (!vd) return

  const sliceData = vd.mpr[props.plane.name]
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

watch(() => [store.windowVal, store.levelVal], draw)
onMounted(() => {
  slice.value = Math.floor((maxSlice.value + 1) / 2)
  draw()
})
</script>

<style scoped>
.mpr-canvas { display: block; width: 100%; aspect-ratio: 1; border-radius: 4px; }
.slider { width: 100%; margin: 4px 0; accent-color: #58a6ff; height: 4px; }
</style>