import { ReaderClient } from './reader-client'

interface Props {
  params: Promise<{ id: string }>
}

export default async function ReaderPage({ params }: Props) {
  const { id } = await params
  return <ReaderClient id={Number(id)} />
}
