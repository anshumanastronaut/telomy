import * as Haptics from 'expo-haptics';
import { SymbolView, SFSymbol } from 'expo-symbols';
import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  TextProps,
  TextStyle,
  View,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ff, fonts, Palette, radius, space, statusColor, statusLabel, usePalette } from '@/lib/theme';

type V = 'display' | 'h1' | 'h2' | 'h3' | 'body' | 'small' | 'label' | 'num' | 'numLg';

export function T({ v = 'body', color, style, ...rest }: TextProps & { v?: V; color?: string }) {
  const p = usePalette();
  const base: Record<V, TextStyle> = {
    display: { fontFamily: fonts.display, fontSize: 34, lineHeight: 40, color: p.text },
    h1: { fontFamily: fonts.display, fontSize: 26, lineHeight: 32, color: p.text },
    h2: { fontFamily: fonts.display, fontSize: 20, lineHeight: 26, color: p.text },
    h3: { fontSize: 16, fontWeight: '600', lineHeight: 22, color: p.text },
    body: { fontSize: 15, lineHeight: 22, color: p.text },
    small: { fontSize: 13, lineHeight: 18, color: p.muted },
    label: { fontSize: 11, letterSpacing: 1.4, fontWeight: '600', textTransform: 'uppercase', color: p.muted },
    num: { fontFamily: fonts.display, fontSize: 24, fontVariant: ['tabular-nums'], color: p.text },
    numLg: { fontFamily: fonts.display, fontSize: 52, lineHeight: 58, fontVariant: ['tabular-nums'], color: p.text },
  };
  const flat = (StyleSheet.flatten([base[v], color ? { color } : null, style]) ?? {}) as TextStyle;
  const isDisplay = flat.fontFamily === fonts.display;
  const family = isDisplay ? fonts.display : ff(flat.fontWeight as any);
  return <Text {...rest} style={[flat, { fontFamily: family, fontWeight: 'normal' }]} maxFontSizeMultiplier={2} />;
}

export function Icon({ name, size = 20, color }: { name: SFSymbol; size?: number; color?: string }) {
  const p = usePalette();
  return <SymbolView name={name} size={size} tintColor={color ?? p.text} weight="regular" />;
}

export function Screen({
  children,
  onRefresh,
  refreshing = false,
  scroll = true,
  edges = ['top'],
  padded = true,
}: {
  children: React.ReactNode;
  onRefresh?: () => void;
  refreshing?: boolean;
  scroll?: boolean;
  edges?: ('top' | 'bottom')[];
  padded?: boolean;
}) {
  const p = usePalette();
  if (!scroll)
    return (
      <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: p.bg }}>
        {children}
      </SafeAreaView>
    );
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: p.bg }}>
      <ScrollView
        contentContainerStyle={{ padding: padded ? space[4] : 0, paddingBottom: 120, gap: space[4] }}
        refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={p.teal} /> : undefined}
        keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function Card({
  children,
  style,
  onPress,
  tone,
  testID,
  accessibilityLabel,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  tone?: 'teal' | 'copper' | 'plain';
  testID?: string;
  accessibilityLabel?: string;
}) {
  const p = usePalette();
  const bg = tone === 'teal' ? p.tealSoft : tone === 'copper' ? p.copperSoft : p.surface;
  const inner = (
    <View style={[{ backgroundColor: bg, borderRadius: radius.lg, borderWidth: 1, borderColor: p.border, padding: space[4], gap: space[2] }, style, onPress ? { width: undefined, flex: undefined, alignSelf: undefined } : null]}>
      {children}
    </View>
  );
  if (!onPress) return inner;
  // Layout props (flex/width) must live on the Pressable, otherwise a tappable card shrinks to its content.
  const flat = (StyleSheet.flatten(style) ?? {}) as ViewStyle;
  const outer: ViewStyle = { flex: flat.flex, width: flat.width, alignSelf: flat.alignSelf };
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      style={({ pressed }) => [outer, { opacity: pressed ? 0.85 : 1 }]}>
      {inner}
    </Pressable>
  );
}

export function Row({ children, gap = space[2], style }: { children: React.ReactNode; gap?: number; style?: StyleProp<ViewStyle> }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap }, style]}>{children}</View>;
}

export function Spacer() {
  return <View style={{ flex: 1 }} />;
}

export function Chip({ label, fg, bg, icon }: { label: string; fg?: string; bg?: string; icon?: SFSymbol }) {
  const p = usePalette();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.pill, backgroundColor: bg ?? p.surfaceAlt, alignSelf: 'flex-start' }}>
      {icon ? <Icon name={icon} size={11} color={fg ?? p.muted} /> : null}
      <Text style={{ fontSize: 11.5, fontFamily: ff('600'), color: fg ?? p.muted  }}>{label}</Text>
    </View>
  );
}

export function StatusChip({ status }: { status?: string | null }) {
  const p = usePalette();
  const c = statusColor(p, status);
  const icon: SFSymbol = status === 'optimal' || status === 'signed' ? 'checkmark' : status === 'out_of_range' || status === 'variant' || status === 'detected' ? 'exclamationmark' : 'circle';
  // Status is carried by text + icon, never colour alone (DS §15.2)
  return <Chip label={statusLabel[status ?? ''] ?? status ?? '—'} fg={c.fg} bg={c.bg} icon={icon} />;
}

/** Provenance chip: source · time · confidence. Every number in Telomy carries one. */
export function Prov({ source, when, confidence }: { source?: string | null; when?: string | null; confidence?: number | null }) {
  const p = usePalette();
  const parts = [source, when].filter(Boolean).join(' · ');
  return (
    <Row gap={6}>
      <Icon name="checkmark.seal" size={11} color={p.faint} />
      <Text style={{ fontSize: 11.5, color: p.faint, fontFamily: fonts.body }} numberOfLines={1}>
        {parts}
        {confidence != null ? ` · ${Math.round(confidence * 100)}% confidence` : ''}
      </Text>
    </Row>
  );
}

/** Confidence gradient: the bar saturates with evidence. */
export function ConfBar({ value, width = 64 }: { value: number; width?: number }) {
  const p = usePalette();
  return (
    <View accessibilityLabel={`Confidence ${Math.round(value * 100)} percent`} style={{ width, height: 4, borderRadius: 2, backgroundColor: p.surfaceAlt, overflow: 'hidden' }}>
      <View style={{ width: `${Math.round(value * 100)}%`, height: 4, backgroundColor: p.teal, opacity: 0.35 + 0.65 * value }} />
    </View>
  );
}

export function Button({
  title,
  onPress,
  kind = 'primary',
  icon,
  disabled,
  loading,
  style,
  testID,
}: {
  title: string;
  onPress: () => void;
  kind?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'copper';
  icon?: SFSymbol;
  disabled?: boolean;
  loading?: boolean;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}) {
  const p = usePalette();
  const bg = { primary: p.teal, copper: p.copper, secondary: p.surface, ghost: 'transparent', danger: p.dangerSoft }[kind];
  const fg = { primary: '#FFFFFF', copper: '#FFFFFF', secondary: p.text, ghost: p.teal, danger: p.danger }[kind];
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={title}
      disabled={disabled || loading}
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      style={({ pressed }) => [
        {
          minHeight: 48,
          borderRadius: radius.md,
          paddingHorizontal: space[4],
          backgroundColor: bg,
          borderWidth: kind === 'secondary' ? 1 : 0,
          borderColor: p.border,
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'row',
          gap: 8,
          opacity: disabled ? 0.45 : pressed ? 0.85 : 1,
        },
        style,
      ]}>
      {loading ? <ActivityIndicator color={fg} /> : icon ? <Icon name={icon} size={16} color={fg} /> : null}
      <Text style={{ color: fg, fontSize: 15, fontFamily: ff('600')  }}>{title}</Text>
    </Pressable>
  );
}

export function Section({ title, action, onAction, children }: { title: string; action?: string; onAction?: () => void; children: React.ReactNode }) {
  const p = usePalette();
  return (
    <View style={{ gap: space[2] }}>
      <Row>
        <T v="label">{title}</T>
        <Spacer />
        {action ? (
          <Pressable onPress={onAction} hitSlop={10} accessibilityRole="button">
            <Text style={{ color: p.teal, fontSize: 13, fontFamily: ff('600')  }}>{action}</Text>
          </Pressable>
        ) : null}
      </Row>
      {children}
    </View>
  );
}

export function Loading({ what }: { what: string }) {
  const p = usePalette();
  return (
    <Row style={{ padding: space[6], justifyContent: 'center' }}>
      <ActivityIndicator color={p.teal} />
      <T v="small">{what}</T>
    </Row>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card tone="copper">
      <T v="h3">That didn't load</T>
      <T v="small">{message}</T>
      {onRetry ? <Button kind="secondary" title="Try again" onPress={onRetry} /> : null}
    </Card>
  );
}

export function Empty({ title, body, actions }: { title: string; body: string; actions?: { title: string; onPress: () => void }[] }) {
  return (
    <Card>
      <T v="h3">{title}</T>
      <T v="small">{body}</T>
      {actions?.map((a) => <Button key={a.title} kind="secondary" title={a.title} onPress={a.onPress} />)}
    </Card>
  );
}

export function ListRow({
  title,
  subtitle,
  right,
  onPress,
  icon,
  testID,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  onPress?: () => void;
  icon?: SFSymbol;
  testID?: string;
}) {
  const p = usePalette();
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : undefined}
      style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: space[3], paddingVertical: space[3], opacity: pressed ? 0.7 : 1, minHeight: 44 })}>
      {icon ? (
        <View style={{ width: 32, height: 32, borderRadius: 8, backgroundColor: p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={icon} size={16} color={p.teal} />
        </View>
      ) : null}
      <View style={{ flex: 1, gap: 2 }}>
        <T v="body" style={{ fontWeight: '500' }}>
          {title}
        </T>
        {subtitle ? <T v="small">{subtitle}</T> : null}
      </View>
      {right}
      {onPress ? <Icon name="chevron.right" size={13} color={p.faint} /> : null}
    </Pressable>
  );
}

export function Divider() {
  const p = usePalette();
  return <View style={{ height: 1, backgroundColor: p.border }} />;
}

export function Segmented<K extends string>({ options, value, onChange }: { options: { key: K; label: string }[]; value: K; onChange: (k: K) => void }) {
  const p = usePalette();
  return (
    <View style={{ flexDirection: 'row', backgroundColor: p.surfaceAlt, borderRadius: radius.md, padding: 3 }}>
      {options.map((o) => {
        const on = o.key === value;
        return (
          <Pressable
            key={o.key}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            onPress={() => onChange(o.key)}
            style={{ flex: 1, paddingVertical: 8, borderRadius: radius.sm, backgroundColor: on ? p.surface : 'transparent', alignItems: 'center' }}>
            <Text style={{ fontSize: 13, fontFamily: ff(600), color: on ? p.text : p.muted  }}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Toast({ text, tone = 'neutral' }: { text: string | null; tone?: 'neutral' | 'success' | 'alert' }) {
  const p = usePalette();
  if (!text) return null;
  const border = tone === 'success' ? p.success : tone === 'alert' ? p.danger : p.border;
  return (
    <View style={{ position: 'absolute', bottom: 100, left: 16, right: 16, backgroundColor: p.surface, borderRadius: radius.md, borderLeftWidth: 4, borderLeftColor: border, padding: space[4], shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 12, elevation: 4 }}>
      <T v="body">{text}</T>
    </View>
  );
}

export function useToast() {
  const [state, setState] = React.useState<{ text: string | null; tone?: 'neutral' | 'success' | 'alert' }>({ text: null });
  const show = React.useCallback((text: string, tone: 'neutral' | 'success' | 'alert' = 'neutral') => {
    setState({ text, tone });
    setTimeout(() => setState({ text: null }), 4000);
  }, []);
  return { toast: <Toast text={state.text} tone={state.tone} />, show };
}

export function Stat({ label, value, unit, sub, color }: { label: string; value: string | number | null | undefined; unit?: string; sub?: string; color?: string }) {
  return (
    <View style={{ flex: 1, gap: 2 }}>
      <T v="label">{label}</T>
      <Row gap={4} style={{ alignItems: 'baseline' }}>
        <T v="num" color={color}>
          {value ?? '—'}
        </T>
        {unit ? <T v="small">{unit}</T> : null}
      </Row>
      {sub ? <T v="small">{sub}</T> : null}
    </View>
  );
}

export type { Palette };
