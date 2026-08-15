import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { Button, ErrorBanner, Field, LoadingBlock, SuccessBanner } from '../../components/ui';
import { fetchGstSettings, updateGstSettings } from '../../lib/settingsApi';
import { apiErrorMessage } from '../franchises/status';

function derivedHalves(rateText: string): { cgst: string; sgst: string; valid: boolean } {
  const rate = Number.parseFloat(rateText);
  if (Number.isNaN(rate) || rate < 0 || rate > 40) {
    return { cgst: '—', sgst: '—', valid: false };
  }
  const cgst = Math.round((rate / 2) * 100) / 100;
  const sgst = Math.round((rate / 2) * 100) / 100;
  const even = Math.round((cgst + sgst) * 100) / 100 === Math.round(rate * 100) / 100;
  return {
    cgst: cgst.toFixed(2),
    sgst: sgst.toFixed(2),
    valid: even,
  };
}

export function GstSettingsPage() {
  const queryClient = useQueryClient();
  const [rate, setRate] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const gstQuery = useQuery({
    queryKey: ['admin-gst'],
    queryFn: fetchGstSettings,
  });

  const current = gstQuery.data;
  const rateText = rate ?? (current ? Number(current.rate).toFixed(2) : '');
  const derived = useMemo(() => derivedHalves(rateText), [rateText]);

  const saveMutation = useMutation({
    mutationFn: () => updateGstSettings(Number.parseFloat(rateText)),
    onSuccess: async (data) => {
      setRate(Number(data.rate).toFixed(2));
      setFeedback('GST rate saved.');
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-gst'] });
    },
    onError: (err) => {
      setFeedback(null);
      setError(apiErrorMessage(err, 'Unable to save GST rate.'));
    },
  });

  if (gstQuery.isLoading) {
    return <LoadingBlock label="Loading GST configuration…" />;
  }

  if (gstQuery.isError || !current) {
    return <ErrorBanner message={apiErrorMessage(gstQuery.error, 'Unable to load GST configuration.')} />;
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-5">
        <h1 className="font-serif text-2xl font-bold text-[#1A1A18]">GST Configuration</h1>
        <p className="text-xs text-[#8A8A84]">
          Configure the total GST rate. CGST and SGST are always 50% each.
        </p>
      </div>

      {feedback ? <div className="mb-4"><SuccessBanner message={feedback} /></div> : null}
      {error ? <div className="mb-4"><ErrorBanner message={error} /></div> : null}

      <div className="rounded-xl border border-[#E0DDD5] bg-white p-5">
        <Field
          label="Current GST Rate (%)"
          type="number"
          min={0}
          max={40}
          step="0.01"
          value={rateText}
          onChange={(e) => {
            setRate(e.target.value);
            setFeedback(null);
          }}
        />

        <div className="mb-4 grid grid-cols-2 gap-3 rounded-lg bg-[#FDFAF4] px-3 py-3 text-sm">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
              Derived CGST
            </div>
            <div className="mt-1 font-semibold text-[#1A1A18]">{derived.cgst}%</div>
          </div>
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[.06em] text-[#8A8A84]">
              Derived SGST
            </div>
            <div className="mt-1 font-semibold text-[#1A1A18]">{derived.sgst}%</div>
          </div>
        </div>

        {!derived.valid && rateText !== '' ? (
          <p className="mb-3 text-xs text-red-600">
            GST must be between 0 and 40 and split evenly into CGST and SGST.
          </p>
        ) : null}

        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending || !derived.valid}
        >
          {saveMutation.isPending ? 'Saving…' : 'Save'}
        </Button>
      </div>
    </div>
  );
}
