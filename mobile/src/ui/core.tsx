import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import { SymbolView, SFSymbol } from 'expo-symbols';
import React from 'react';
import {
  ActivityIndicator,
  Dimensions,
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

import { depth, ff, fonts, Palette, radius, space, statusColor, statusLabel, usePalette } from '@/lib/theme';
import { TelomyLoader } from './loader';

type V = 'display' | 'h1' | 'h2' | 'h3' | 'body' | 'small' | 'label' | 'num' | 'numLg';

export function T({ v = 'body', color, style, ...rest }: TextProps & { v?: V; color?: string }) {
  const p = usePalette();
  const base: Record<V, TextStyle> = {
    // Editorial hierarchy: Fraunces carries every headline and number, Inter carries reading and UI. Tight negative
    // tracking on large serif sizes, generous line-height on body, one quiet micro-label style.
    // Telomy brand face is a hero-only accent (h1 = each screen's title). display carries big numbers → mono.
    display: { fontFamily: fonts.mono, fontSize: 44, lineHeight: 50, color: p.text, letterSpacing: -1.5, fontVariant: ['tabular-nums'] },
    h1: { fontFamily: fonts.display, fontSize: 32, lineHeight: 38, color: p.text, letterSpacing: 0.5 },
    h2: { fontSize: 23, fontWeight: '600', lineHeight: 29, color: p.text, letterSpacing: -0.2 },
    h3: { fontSize: 17, fontWeight: '600', lineHeight: 23, color: p.text, letterSpacing: -0.2 },
    body: { fontSize: 16, lineHeight: 24, color: p.text },
    small: { fontSize: 14, lineHeight: 20, color: p.muted },
    label: { fontSize: 12, letterSpacing: 0.6, fontWeight: '600', color: p.muted },
    num: { fontFamily: fonts.mono, fontSize: 25, fontVariant: ['tabular-nums'], color: p.text, letterSpacing: -0.6 },
    numLg: { fontFamily: fonts.mono, fontSize: 52, lineHeight: 58, fontVariant: ['tabular-nums'], color: p.text, letterSpacing: -2 },
  };
  const flat = (StyleSheet.flatten([base[v], color ? { color } : null, style]) ?? {}) as TextStyle;
  // Honour an explicit family (display serif / mono numerals); otherwise pick the UI weight.
  const family = flat.fontFamily ?? ff(flat.fontWeight as any);
  // Native uppercase turns "µg/m³" into "ΜG/M³" (Greek capital mu); uppercase by hand and keep µ-units intact.
  if (flat.textTransform === 'uppercase' && typeof rest.children === 'string' && rest.children.includes('µ')) {
    const text = rest.children.split(/(µ[A-Za-z]+(?:\/[A-Za-z0-9³²]+)?)/).map((s, i) => (i % 2 ? s : s.toUpperCase())).join('');
    return <Text {...rest} style={[flat, { fontFamily: family, fontWeight: 'normal', textTransform: 'none' }]} maxFontSizeMultiplier={2}>{text}</Text>;
  }
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
  scrollEnabled = true,
}: {
  children: React.ReactNode;
  onRefresh?: () => void;
  refreshing?: boolean;
  scroll?: boolean;
  /** false while a child (e.g. the 3D twin) owns the gesture, so the page doesn't scroll under it */
  scrollEnabled?: boolean;
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
        scrollEnabled={scrollEnabled}
        contentContainerStyle={{ paddingHorizontal: padded ? space[5] : 0, paddingTop: padded ? space[3] : 0, paddingBottom: 132, gap: space[4] }}
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
    // No outlines: depth comes from surface tone (dark) or a soft shadow (light). Larger radius + padding = calmer.
    <View style={[{ backgroundColor: bg, borderRadius: radius.xl, padding: space[5], gap: space[3] },
      p.isDark ? null : { shadowColor: depth.shadow, shadowOpacity: 0.06, shadowRadius: 14, shadowOffset: { width: 0, height: 4 } },
      style, onPress ? { width: undefined, flex: undefined, alignSelf: undefined } : null]}>
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
      style={({ pressed }) => [outer, { opacity: pressed ? 0.9 : 1, transform: [{ scale: pressed ? 0.985 : 1 }] }]}>
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
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill, backgroundColor: bg ?? p.surfaceAlt, alignSelf: 'flex-start' }}>
      {icon ? <Icon name={icon} size={12} color={fg ?? p.muted} /> : null}
      <Text style={{ fontSize: 12.5, fontFamily: ff('600'), color: fg ?? p.muted }}>{label}</Text>
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
  const bg = { primary: p.teal, copper: p.copper, secondary: p.surfaceAlt, ghost: 'transparent', danger: p.dangerSoft }[kind];
  // dark-first: bright teal/copper fills carry ink text for contrast; light mode keeps white on deep teal
  const onFill = p.onAccent;
  const fg = { primary: onFill, copper: onFill, secondary: p.text, ghost: p.teal, danger: p.danger }[kind];
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={title}
      disabled={disabled || loading}
      onPress={() => {
        // haptics only where they earn their place: commits get a light impact, plain navigation none
        if (kind === 'primary' || kind === 'copper' || kind === 'danger') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        onPress();
      }}
      style={({ pressed }) => [
        {
          minHeight: 50,
          borderRadius: radius.pill,
          paddingHorizontal: space[5],
          backgroundColor: bg,
          borderWidth: 0,
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
    // Sections open with an editorial serif title (not tiny caps) and sit further from the previous section than
    // their own items sit from each other — proximity does the grouping, not boxes.
    <View style={{ gap: space[3], marginTop: space[3] }}>
      <Row style={{ alignItems: 'baseline' }}>
        <T v="h2" style={{ flex: 1 }}>{/[a-z]/.test(title) ? title : title.charAt(0) + title.slice(1).toLowerCase()}</T>
        {action ? (
          <Pressable onPress={onAction} hitSlop={10} accessibilityRole="button">
            <Text style={{ color: p.teal, fontSize: 14, fontFamily: ff('600') }}>{action}</Text>
          </Pressable>
        ) : null}
      </Row>
      {children}
    </View>
  );
}

/** A back control for screens that don't get a native header (e.g. detail screens inside the doctor/centre tab
 * groups). Place it at the top of the Screen. Falls back to a route when there's no stack history to pop. */
export function BackButton({ label = 'Back', fallback }: { label?: string; fallback?: string }) {
  const p = usePalette();
  return (
    <Pressable
      onPress={() => { if (router.canGoBack()) router.back(); else if (fallback) router.replace(fallback as any); }}
      accessibilityRole="button" accessibilityLabel={label} hitSlop={10}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 2, alignSelf: 'flex-start', paddingVertical: 4, marginBottom: 2 }}>
      <Icon name="chevron.left" size={17} color={p.teal} />
      <T v="body" color={p.teal}>{label}</T>
    </Pressable>
  );
}

export function Loading({ what }: { what: string }) {
  // Centre the motion mark in the viewport (not pinned to the top of the scroll view).
  const h = Dimensions.get('window').height;
  return (
    <View style={{ minHeight: h * 0.9, alignItems: 'center', justifyContent: 'center' }}>
      <TelomyLoader size="hero" message={what} />
    </View>
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
  tint,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  onPress?: () => void;
  icon?: SFSymbol;
  testID?: string;
  /** Colour the icon only when it carries meaning (a data signal, a warning). Default is neutral — colour is for data. */
  tint?: string;
}) {
  const p = usePalette();
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : undefined}
      style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: space[3], paddingVertical: space[3], opacity: pressed ? 0.6 : 1, minHeight: 48 })}>
      {icon ? (
        <View style={{ width: 32, height: 32, borderRadius: radius.sm + 2, backgroundColor: tint ? tint + '22' : p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={icon} size={15} color={tint ?? p.graphite} />
        </View>
      ) : null}
      <View style={{ flex: 1, gap: 2 }}>
        <T v="body" style={{ fontWeight: '500' }} numberOfLines={1}>
          {title}
        </T>
        {subtitle ? <T v="small" numberOfLines={2}>{subtitle}</T> : null}
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
    <View style={{ flexDirection: 'row', backgroundColor: p.surfaceAlt, borderRadius: radius.pill, padding: 3 }}>
      {options.map((o) => {
        const on = o.key === value;
        return (
          <Pressable
            key={o.key}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            onPress={() => { if (o.key !== value) Haptics.selectionAsync().catch(() => {}); onChange(o.key); }}
            style={{ flex: 1, paddingVertical: 9, borderRadius: radius.pill, backgroundColor: on ? (p.isDark ? p.borderStrong : p.surface) : 'transparent', alignItems: 'center',
              shadowColor: '#000', shadowOpacity: on ? 0.15 : 0, shadowRadius: 4, shadowOffset: { width: 0, height: 1 } }}>
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
    <View style={{ position: 'absolute', bottom: 104, left: 16, right: 16, backgroundColor: p.surfaceAlt, borderRadius: radius.lg, borderLeftWidth: 4, borderLeftColor: border, padding: space[4], shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 12, elevation: 4 }}>
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
        <T v="num" color={color} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.5} style={{ flexShrink: 1 }}>
          {value ?? '—'}
        </T>
        {unit ? <T v="small">{unit}</T> : null}
      </Row>
      {sub ? <T v="small">{sub}</T> : null}
    </View>
  );
}

export type { Palette };
