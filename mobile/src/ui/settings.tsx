// Reusable settings controls for the staff hubs (doctor / centre). Each row is label + control, styled to the
// palette, and reports changes up. Persisting is the caller's job (PUT the changed key; the backend merges).
import React from 'react';
import { Switch, TextInput, View } from 'react-native';

import { radius, space, usePalette } from '@/lib/theme';
import { Icon, Row, T } from './core';

function Shell({ icon, title, subtitle, right, children }: { icon?: any; title: string; subtitle?: string; right?: React.ReactNode; children?: React.ReactNode }) {
  const p = usePalette();
  return (
    <View style={{ paddingVertical: 10, gap: children ? 8 : 0 }}>
      <Row style={{ alignItems: 'center' }} gap={10}>
        {icon ? <Icon name={icon} size={18} color={p.muted} /> : null}
        <View style={{ flex: 1 }}>
          <T v="body">{title}</T>
          {subtitle ? <T v="small" color={p.muted} style={{ marginTop: 1 }}>{subtitle}</T> : null}
        </View>
        {right}
      </Row>
      {children}
    </View>
  );
}

export function SwitchRow({ icon, title, subtitle, value, onValueChange }: { icon?: any; title: string; subtitle?: string; value: boolean; onValueChange: (v: boolean) => void }) {
  const p = usePalette();
  return (
    <Shell icon={icon} title={title} subtitle={subtitle}
      right={<Switch value={value} onValueChange={onValueChange} trackColor={{ true: p.teal, false: p.surfaceAlt }} thumbColor="#fff" ios_backgroundColor={p.surfaceAlt} />} />
  );
}

export function StepperRow({ icon, title, subtitle, value, min = 0, max = 999, step = 1, unit, onChange }: { icon?: any; title: string; subtitle?: string; value: number; min?: number; max?: number; step?: number; unit?: string; onChange: (v: number) => void }) {
  const p = usePalette();
  const clamp = (v: number) => Math.max(min, Math.min(max, v));
  const btn = (label: string, to: number, disabled: boolean) => (
    <View
      onStartShouldSetResponder={() => !disabled}
      onResponderRelease={() => !disabled && onChange(clamp(to))}
      style={{ width: 34, height: 34, borderRadius: radius.sm, alignItems: 'center', justifyContent: 'center', backgroundColor: disabled ? p.surfaceAlt : p.tealSoft, opacity: disabled ? 0.5 : 1 }}>
      <T v="h3" color={disabled ? p.faint : p.teal}>{label}</T>
    </View>
  );
  return (
    <Shell icon={icon} title={title} subtitle={subtitle}
      right={
        <Row gap={8} style={{ alignItems: 'center' }}>
          {btn('−', value - step, value <= min)}
          <T v="body" style={{ minWidth: 54, textAlign: 'center' }}>{value}{unit ? ` ${unit}` : ''}</T>
          {btn('+', value + step, value >= max)}
        </Row>
      } />
  );
}

export function TextRow({ icon, title, placeholder, value, onChangeText, keyboardType, multiline }: { icon?: any; title: string; placeholder?: string; value: string; onChangeText: (v: string) => void; keyboardType?: any; multiline?: boolean }) {
  const p = usePalette();
  return (
    <Shell icon={icon} title={title}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={p.faint}
        keyboardType={keyboardType}
        multiline={multiline}
        style={{ backgroundColor: p.surface, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, color: p.text, fontFamily: 'HankenGrotesk_400Regular', fontSize: 15, minHeight: multiline ? 72 : undefined, textAlignVertical: multiline ? 'top' : 'center' }}
      />
    </Shell>
  );
}

export function ChoiceRow<K extends string>({ icon, title, subtitle, options, value, onChange }: { icon?: any; title: string; subtitle?: string; options: { key: K; label: string }[]; value: K; onChange: (k: K) => void }) {
  const p = usePalette();
  return (
    <Shell icon={icon} title={title} subtitle={subtitle}>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
        {options.map((o) => {
          const on = o.key === value;
          return (
            <View key={o.key} onStartShouldSetResponder={() => true} onResponderRelease={() => onChange(o.key)}
              style={{ paddingHorizontal: 12, paddingVertical: 7, borderRadius: radius.pill, backgroundColor: on ? p.teal : p.surface, borderWidth: on ? 0 : 1, borderColor: p.border }}>
              <T v="small" color={on ? '#fff' : p.text}>{o.label}</T>
            </View>
          );
        })}
      </View>
    </Shell>
  );
}
