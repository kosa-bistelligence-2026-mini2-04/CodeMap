import '@testing-library/jest-dom/vitest';

type UUID = `${string}-${string}-${string}-${string}-${string}`;

const generateUuid = (): UUID =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  }) as UUID;

if (typeof globalThis.crypto === 'undefined') {
  // jsdom environments without webcrypto fallback
  // @ts-expect-error inject minimal randomUUID for tests
  globalThis.crypto = {
    randomUUID: generateUuid,
  };
}

