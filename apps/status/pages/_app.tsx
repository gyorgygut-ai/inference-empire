import '@mantine/core/styles.css'
import type { AppProps } from 'next/app'
import { MantineProvider, ColorSchemeScript } from '@mantine/core'
import NoSsr from '@/components/NoSsr'
import '@/util/i18n'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <ColorSchemeScript defaultColorScheme="auto" />
      <NoSsr>
        <MantineProvider defaultColorScheme="auto">
          <Component {...pageProps} />
        </MantineProvider>
      </NoSsr>
    </>
  )
}
