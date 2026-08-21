import { Check } from 'lucide-react';

import {
  deriveLaunchProgress,
  type DerivedLaunchProgress,
  type DerivedLaunchStage,
  type LaunchProgressSource,
} from './launchStages';

function stageDotClass(state: DerivedLaunchStage['state']): string {
  if (state === 'completed') return 'border-[#1A7A4A] bg-[#1A7A4A] text-white';
  if (state === 'current') return 'border-[#E8621A] bg-white text-[#E8621A]';
  return 'border-[#E0DDD5] bg-[#FDFAF4] text-[#8A8A84]';
}

function connectorClass(complete: boolean): string {
  return complete ? 'bg-[#1A7A4A]' : 'bg-[#E0DDD5]';
}

function StageMarker({ stage, index }: { stage: DerivedLaunchStage; index: number }) {
  return (
    <span
      className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-[11px] font-bold ${stageDotClass(stage.state)}`}
      aria-hidden="true"
    >
      {stage.state === 'completed' ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : index + 1}
    </span>
  );
}

function stageStatusLabel(stage: DerivedLaunchStage): string {
  if (stage.state === 'completed') return 'Completed';
  if (stage.state === 'current') return 'Current';
  return 'Pending';
}

function StageCopy({ stage, align }: { stage: DerivedLaunchStage; align: 'left' | 'center' }) {
  return (
    <div className={align === 'center' ? 'text-center' : ''}>
      <div
        className={`text-sm font-semibold ${
          stage.state === 'pending' ? 'text-[#8A8A84]' : 'text-[#1A1A18]'
        }`}
      >
        {stage.label}
      </div>
      <div
        className={`text-[11px] ${
          stage.state === 'current'
            ? 'font-semibold text-[#E8621A]'
            : stage.state === 'completed'
              ? 'text-[#1A7A4A]'
              : 'text-[#8A8A84]'
        }`}
      >
        {stageStatusLabel(stage)}
      </div>
    </div>
  );
}

export function LaunchProgressTrack({ source }: { source: LaunchProgressSource }) {
  const progress = deriveLaunchProgress(source);

  return (
    <div className="rounded-[10px] border border-[#E0DDD5] bg-white px-4 py-4">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-serif text-xl font-bold text-[#1A1A18]">Launch Progress</h2>
        <p className="text-xs text-[#8A8A84]">
          {progress.allComplete
            ? 'All stages complete'
            : `${progress.completedCount} of ${progress.totalCount} complete`}
        </p>
      </div>

      <ol className="sm:hidden">
        {progress.stages.map((stage, index) => (
          <li
            key={stage.key}
            className="flex gap-3"
            aria-current={stage.state === 'current' ? 'step' : undefined}
          >
            <div className="flex w-7 shrink-0 flex-col items-center">
              <StageMarker stage={stage} index={index} />
              {index < progress.stages.length - 1 ? (
                <span
                  className={`w-px flex-1 min-h-4 ${connectorClass(stage.state === 'completed')}`}
                  aria-hidden="true"
                />
              ) : null}
            </div>
            <div className={index < progress.stages.length - 1 ? 'pb-4' : 'pb-0'}>
              <StageCopy stage={stage} align="left" />
            </div>
          </li>
        ))}
      </ol>

      <ol className="hidden sm:flex sm:items-start">
        {progress.stages.map((stage, index) => (
          <li
            key={stage.key}
            className="min-w-0 flex-1"
            aria-current={stage.state === 'current' ? 'step' : undefined}
          >
            <div className="flex items-center">
              <span
                className={`h-0.5 flex-1 ${index === 0 ? 'bg-transparent' : connectorClass(progress.stages[index - 1].state === 'completed')}`}
                aria-hidden="true"
              />
              <StageMarker stage={stage} index={index} />
              <span
                className={`h-0.5 flex-1 ${
                  index === progress.stages.length - 1
                    ? 'bg-transparent'
                    : connectorClass(stage.state === 'completed')
                }`}
                aria-hidden="true"
              />
            </div>
            <div className="mt-2 px-1">
              <StageCopy stage={stage} align="center" />
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function LaunchProgressCompact({
  source,
  showShortLabel = false,
}: {
  source: LaunchProgressSource;
  showShortLabel?: boolean;
}) {
  const progress = deriveLaunchProgress(source);
  const label = showShortLabel ? progress.currentShortLabel : progress.currentLabel;

  return (
    <div className="min-w-[6.5rem]" title={progress.currentLabel}>
      <LaunchProgressDots progress={progress} />
      <div className="mt-1 text-xs font-medium text-[#1A1A18]">{label}</div>
    </div>
  );
}

export function LaunchProgressDots({ progress }: { progress: DerivedLaunchProgress }) {
  return (
    <div className="flex items-center gap-1" aria-label={`Launch: ${progress.currentLabel}`}>
      {progress.stages.map((stage) => (
        <span
          key={stage.key}
          className={`h-2 w-2 rounded-full ${
            stage.state === 'completed'
              ? 'bg-[#1A7A4A]'
              : stage.state === 'current'
                ? 'bg-[#E8621A]'
                : 'bg-[#E0DDD5]'
          }`}
          title={`${stage.label}: ${stageStatusLabel(stage)}`}
        />
      ))}
    </div>
  );
}
