<template>
  <div ref="container" class="viewer3d"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useImagingStore } from '../store/imaging'
import {
  axisSize,
  voxelAt,
  type AxisKey,
} from '../volumeGeometry'

const store = useImagingStore()
const container = ref<HTMLDivElement>()
let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer, controls: OrbitControls, animId: number
let volGroup = new THREE.Group()

function initScene() {
  const c = container.value!
  scene = new THREE.Scene(); scene.background = new THREE.Color(0x0d1117)
  camera = new THREE.PerspectiveCamera(45, c.clientWidth/c.clientHeight, 0.1, 50); camera.position.set(3, 2, 4)
  renderer = new THREE.WebGLRenderer({ antialias: true }); renderer.setSize(c.clientWidth, c.clientHeight)
  c.appendChild(renderer.domElement)
  controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.target.set(0, 0, 0)
  scene.add(new THREE.AmbientLight(0xffffff, 0.6))
  scene.add(volGroup)
}

function renderVolume() {
  volGroup.clear()
  const vd = store.volumeData
  if (!vd) return

  const coordinateSystem = vd.coordinateSystem
  const sizes = coordinateSystem.axes.reduce((acc, axis) => {
    acc[axis.key] = axisSize(vd.dimensions, coordinateSystem, axis.key)
    return acc
  }, {} as Record<AxisKey, number>)
  const step = 2

  const wl = store.windowVal, ww = store.levelVal
  const lower = wl - ww/2, upper = wl + ww/2

  // Sample volume as point cloud with transfer function
  const positions: number[] = [], colors: number[] = []
  const scaleByAxis = {
    x: 3 / sizes.x,
    y: 3 / sizes.y,
    z: 3 / sizes.z,
  }

  for (let z = 0; z < sizes.z; z += step) {
    for (let y = 0; y < sizes.y; y += step) {
      for (let x = 0; x < sizes.x; x += step) {
        const position = { x, y, z }
        const val = voxelAt(vd.volume, vd.dimensions, coordinateSystem, position)
        if (val === undefined) continue

        let t = (val - lower) / (upper - lower)
        t = Math.max(0, Math.min(1, t))

        if (t > 0.05) {
          positions.push(
            (position.x - sizes.x / 2) * scaleByAxis.x,
            (position.y - sizes.y / 2) * scaleByAxis.y,
            (position.z - sizes.z / 2) * scaleByAxis.z
          )
          // Bone (white), tissue (gray), air (transparent)
          const alpha = t * 0.6
          colors.push(0.8 + t*0.2, 0.7 + t*0.2, 0.6 + t*0.3)
        }
      }
    }
  }

  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  const mat = new THREE.PointsMaterial({ size: 0.04, vertexColors: true, blending: THREE.AdditiveBlending, depthWrite: true, transparent: true, opacity: 0.8 })
  volGroup.add(new THREE.Points(geom, mat))

  // Axes cross
  const axGeom = new THREE.BufferGeometry()
  axGeom.setAttribute('position', new THREE.Float32BufferAttribute([-2,0,0,2,0,0,0,-2,0,0,2,0,0,0,-2,0,0,2], 3))
  volGroup.add(new THREE.Line(axGeom, new THREE.LineBasicMaterial({ color: 0x30363d })))
}

function animate() { animId = requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera) }

onMounted(() => { initScene(); animate() })
watch(() => [store.volumeData, store.windowVal, store.levelVal], renderVolume, { deep: true })
onUnmounted(() => { cancelAnimationFrame(animId); renderer?.dispose() })
</script>
<style scoped>.viewer3d{width:100%;height:100%;min-height:400px}</style>