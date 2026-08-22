import type { FranchiseStatus } from '../../types/franchise';

export const LAUNCH_STAGES = [
  { key: 'created', label: 'Franchise Created', shortLabel: 'Created' },
  { key: 'payment', label: 'Payment Received', shortLabel: 'Payment' },
  { key: 'ready', label: 'Ready to Launch', shortLabel: 'Ready' },
] as const;

export type LaunchStageKey = (typeof LAUNCH_STAGES)[number]['key'];
export type LaunchStageVisualState = 'completed' | 'current' | 'pending';

export type LaunchProgressSource = {
  status: FranchiseStatus;
  payment_status?: string | null;
};

export type DerivedLaunchStage = (typeof LAUNCH_STAGES)[number] & {
  state: LaunchStageVisualState;
};

export type DerivedLaunchProgress = {
  stages: DerivedLaunchStage[];
  completedCount: number;
  totalCount: number;
  currentLabel: string;
  currentShortLabel: string;
  allComplete: boolean;
};

/** Latest franchise_payments.status already exposed by the franchise APIs. */
export function isPaymentReceived(paymentStatus: string | null | undefined): boolean {
  return paymentStatus === 'COMPLETED';
}

/**
 * ACTIVE is the existing operational franchise status.
 * SUSPENDED and CLOSED are post-launch states — the outlet already passed ready-to-launch.
 * This is only the status half of Ready to Launch; payment must also be COMPLETED.
 */
export function isReadyToLaunch(status: FranchiseStatus): boolean {
  return status === 'ACTIVE' || status === 'SUSPENDED' || status === 'CLOSED';
}

export function deriveLaunchProgress(source: LaunchProgressSource): DerivedLaunchProgress {
  const paymentReceived = isPaymentReceived(source.payment_status);
  const flags = [
    true,
    paymentReceived,
    paymentReceived && isReadyToLaunch(source.status),
  ];
  const firstIncomplete = flags.findIndex((done) => !done);

  const stages: DerivedLaunchStage[] = LAUNCH_STAGES.map((stage, index) => {
    let state: LaunchStageVisualState;
    if (flags[index]) {
      state = 'completed';
    } else if (index === firstIncomplete) {
      state = 'current';
    } else {
      state = 'pending';
    }
    return { ...stage, state };
  });

  const completedCount = flags.filter(Boolean).length;
  const allComplete = completedCount === flags.length;
  const current = stages.find((stage) => stage.state === 'current') ?? stages[stages.length - 1];

  return {
    stages,
    completedCount,
    totalCount: stages.length,
    currentLabel: current.label,
    currentShortLabel: current.shortLabel,
    allComplete,
  };
}
