import { Center, Text, Container } from '@mantine/core'
import Header from '@/components/Header'
import Footer from '@/components/Footer'

export default function Custom500() {
  return (
    <>
      <Header />
      <Center style={{ height: 'calc(100vh - 120px)' }}>
        <Container>
          <Text size="xl" fw={700} ta="center">
            500 - Internal Server Error
          </Text>
        </Container>
      </Center>
      <Footer />
    </>
  )
}
