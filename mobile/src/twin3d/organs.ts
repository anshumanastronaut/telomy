// Shared by the native and web 3D twin: which 3D organs represent each Twin organ-map system, and their labels.
import type { OrganId } from './scene';

/** Twin organ-map system name → the 3D organs that represent it. */
export const SYSTEM_ORGANS: Record<string, OrganId[]> = {
  'Heart & vessels': ['heart', 'vessels'],
  'Blood sugar & metabolism': ['pancreas', 'stomach'],
  Liver: ['liver'],
  'Lungs & cardio fitness': ['lungs'],
  'Muscle & bone': ['skeleton'],
  'Recovery & sleep': ['brain'],
  Nutrients: ['intestines'],
};
export const ORGAN_LABEL: Record<OrganId, string> = {
  brain: 'Brain & nervous system', lungs: 'Lungs', heart: 'Heart', vessels: 'Blood vessels', liver: 'Liver',
  stomach: 'Stomach', pancreas: 'Pancreas', kidneys: 'Kidneys', intestines: 'Gut', bladder: 'Bladder',
  skeleton: 'Skeleton & muscle',
};
export const systemOfOrgan = (o: OrganId) => Object.entries(SYSTEM_ORGANS).find(([, os]) => os.includes(o))?.[0] ?? null;

