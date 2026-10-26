import { useLocalSearchParams } from 'expo-router';
import { Copilot } from '@/ui/copilot';

export default function DoctorCopilot() {
  const { pid, name } = useLocalSearchParams<{ pid?: string; name?: string }>();
  return <Copilot role="doctor" patientId={pid} patientName={name} />;
}
