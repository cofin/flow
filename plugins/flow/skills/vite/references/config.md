# Vite Configuration Reference

## Basic Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
        },
      },
    },
  },
});
```

## Custom Plugin

```typescript
import type { Plugin, ViteDevServer } from 'vite';

export function myPlugin(options: MyPluginOptions = {}): Plugin {
  return {
    name: 'vite-plugin-my-plugin',
    enforce: 'pre', // or 'post'

    // Configuration hook
    config(config, env) {
      return {
        define: {
          __MY_VAR__: JSON.stringify(options.myVar),
        },
      };
    },

    // Server configuration
    configureServer(server: ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        // Custom middleware
        next();
      });
    },

    // Transform hook
    transform(code, id) {
      if (!id.endsWith('.custom')) return null;
      return {
        code: transformCode(code),
        map: null,
      };
    },

    // Build hooks
    buildStart() {
      console.log('Build started');
    },

    buildEnd() {
      console.log('Build ended');
    },
  };
}
```

## Environment Variables

```typescript
// vite.config.ts
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    define: {
      'process.env.API_URL': JSON.stringify(env.API_URL),
    },
  };
});

// In code: import.meta.env.VITE_API_URL
```

## Library Mode

```typescript
// vite.config.ts for building a library
import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [dts()],
  build: {
    lib: {
      entry: 'src/index.ts',
      name: 'MyLib',
      formats: ['es', 'cjs', 'umd'],
      fileName: (format) => `my-lib.${format}.js`,
    },
    rollupOptions: {
      external: ['react', 'react-dom'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
  },
});
```

## Asset Handling

```typescript
// Import as URL
import imgUrl from './img.png';

// Import as string (raw)
import shaderCode from './shader.glsl?raw';

// Import as worker
import Worker from './worker.js?worker';

// Dynamic import with glob
const modules = import.meta.glob('./modules/*.ts');
const eagerModules = import.meta.glob('./modules/*.ts', { eager: true });
```

## SSR Configuration

```typescript
// vite.config.ts
export default defineConfig({
  ssr: {
    external: ['some-external-package'],
    noExternal: ['package-to-bundle'],
  },
  build: {
    ssr: true,
    rollupOptions: {
      input: 'src/entry-server.ts',
    },
  },
});
```

## Best Practices

- Use `defineConfig` for type safety
- Externalize heavy dependencies in library mode
- Use `optimizeDeps.include` for pre-bundling issues
- Configure proper aliases for clean imports
- Use environment-specific configs with mode
