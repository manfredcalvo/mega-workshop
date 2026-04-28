import { defineConfig } from 'tsdown';

export default defineConfig({
  entry: ['./src/index.ts'],
  format: ['esm'],
  target: 'node22',
  unbundle: false,
  external: [/^express/, /^cors/, /^dotenv/, /^zod/, /^ai/],
  noExternal: [/@chat-template\/.*/, /@databricks\/ai-sdk-provider/],
  dts: false,
});
