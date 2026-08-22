import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  ACTION_FIT_CLASS,
  ACTION_GROUP_CLASS,
  ACTION_SELECT_CLASS,
  ACTIONS_TD_CLASS,
  ACTIONS_TH_CLASS,
} from '../src/components/ui/actionFit.ts';

function minWidthRem(className: string): number {
  const match = className.match(/min-w-\[([0-9.]+)rem\]/);
  assert.ok(match, `expected min-w rem token in: ${className}`);
  return Number(match[1]);
}

describe('action fit tokens', () => {
  it('locks Activate and Deactivate to the same status width', () => {
    assert.match(ACTION_FIT_CLASS.status, /h-8/);
    assert.match(ACTION_FIT_CLASS.status, /min-w-\[7\.5rem\]/);
    assert.match(ACTION_FIT_CLASS.status, /whitespace-nowrap/);
    assert.equal(minWidthRem(ACTION_FIT_CLASS.status), minWidthRem(ACTION_FIT_CLASS.status));
  });

  it('keeps short actions narrower than status and long actions', () => {
    assert.ok(minWidthRem(ACTION_FIT_CLASS.sm) < minWidthRem(ACTION_FIT_CLASS.status));
    assert.ok(minWidthRem(ACTION_FIT_CLASS.status) < minWidthRem(ACTION_FIT_CLASS.lg));
    assert.ok(minWidthRem(ACTION_FIT_CLASS.lg) < minWidthRem(ACTION_FIT_CLASS.xl));
  });

  it('uses square dimensions for icon-only actions', () => {
    assert.match(ACTION_FIT_CLASS.icon, /h-8/);
    assert.match(ACTION_FIT_CLASS.icon, /w-8/);
    assert.match(ACTION_FIT_CLASS.icon, /min-w-8/);
    assert.match(ACTION_FIT_CLASS.icon, /p-0/);
  });

  it('wraps action groups on small screens with consistent gap', () => {
    assert.match(ACTION_GROUP_CLASS, /flex-wrap/);
    assert.match(ACTION_GROUP_CLASS, /gap-1\.5/);
    assert.match(ACTION_GROUP_CLASS, /max-w-\[16\.5rem\]/);
    assert.match(ACTION_GROUP_CLASS, /md:max-w-none/);
  });

  it('aligns ACTIONS header and cell consistently', () => {
    assert.match(ACTIONS_TH_CLASS, /text-left/);
    assert.match(ACTIONS_TD_CLASS, /text-left/);
    assert.match(ACTIONS_TD_CLASS, /align-middle/);
  });

  it('matches action-select height to action buttons', () => {
    assert.match(ACTION_SELECT_CLASS, /h-8/);
    assert.match(ACTION_SELECT_CLASS, /rounded-lg/);
  });
});
