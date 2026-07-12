export type BookStatus = 'generating' | 'done' | 'error'

export type BookType =
  | 'childrens'
  | 'tutorial'
  | 'guide'
  | 'educational'
  | 'story'
  | 'custom'

export interface Book {
  id: number
  title: string
  prompt: string
  book_type: BookType
  page_count: number
  illustration_style: string
  status: BookStatus
  cover_hue: number
  favorite: boolean
  progress: number
  progress_label: string
  use_research: boolean
  writing_style: string | null
  created_at: string
  last_modified: string | null
  outline: string | null
  content: string | null
  error_message: string | null
}

export interface BookCreate {
  title: string
  prompt: string
  book_type: BookType
  page_count: number
  illustration_style: string
  cover_hue: number
  use_research: boolean
  writing_style?: string
}

export interface Credits {
  remaining: number
  total: number
}
