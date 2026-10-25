import { strategyBeam } from "../strategies/strategy-beam";
import { strategyModal } from "../strategies/strategy-modal";
import { strategyFlash } from "../strategies/strategy-flash";

type Strategy = {
  resolveConfig: () => any;
  pushToTaskQueue: (input: any, config: any) => Promise<{ task_id: string }>;
  fetchTaskStatus: (taskId: string, config: any) => Promise<{ status: string; output?: any }>;
};

export function createStrategy(name: string): Strategy | null {
  switch (name) {
    case "beam":
      return strategyBeam;
    case "modal":
      return strategyModal;
    case "flash":
      return strategyFlash;
    default:
      return null;
  }
}
