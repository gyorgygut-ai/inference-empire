import { ref } from 'vue'

export function useProbe(action: () => Promise<string>) {
  const loading = ref(false)
  const result = ref<{ status: 'success' | 'failure'; message: string } | null>(null)

  async function run() {
    loading.value = true
    result.value = null
    try {
      result.value = { status: 'success', message: await action() }
    } catch (error) {
      result.value = { status: 'failure', message: String(error) }
    } finally {
      loading.value = false
    }
  }

  return { loading, result, run }
}
