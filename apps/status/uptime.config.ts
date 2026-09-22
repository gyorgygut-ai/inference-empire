import { MaintenanceConfig, PageConfig, WorkerConfig } from './types/config'

const pageConfig: PageConfig = {
  title: 'Status',
  logo: '/logo.png',
  customFooter: '',
  links: [],
  group: {},
}

const workerConfig: WorkerConfig = {
  monitors: [],
}

const maintenances: MaintenanceConfig[] = []

export { maintenances, pageConfig, workerConfig }
