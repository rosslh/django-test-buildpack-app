/// <reference types="vite/client" />

// Type declarations for unplugin-icons
declare module '~icons/*' {
  import { ComponentType, SVGProps } from 'react'
  const component: ComponentType<SVGProps<SVGSVGElement>>
  export default component
}
