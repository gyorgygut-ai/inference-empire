import { Center, Text, Container } from '@mantine/core'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { NextPage } from 'next'

interface ErrorProps {
  statusCode?: number
}

const Error: NextPage<ErrorProps> = ({ statusCode }) => {
  return (
    <>
      <Header />
      <Center style={{ height: 'calc(100vh - 120px)' }}>
        <Container>
          <Text size="xl" fw={700} ta="center">
            {statusCode 
              ? `${statusCode} - An error occurred on the server` 
              : 'An unexpected error occurred'}
          </Text>
        </Container>
      </Center>
      <Footer />
    </>
  )
}

Error.getInitialProps = async ({ res }: any) => {
  const statusCode = res ? res.statusCode : 500
  return { statusCode }
}

export default Error
