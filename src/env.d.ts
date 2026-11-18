/// <reference types="astro/client" />

interface ImportMetaEnv {
  /** Base URL of the SecondServe API, e.g. http://192.168.1.20:5050/api. Leave unset to run on seed data. */
  readonly PUBLIC_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
