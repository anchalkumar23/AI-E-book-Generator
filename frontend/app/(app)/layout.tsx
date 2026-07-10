import s from './layout.module.css'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={s.shell}>
      {children}
    </div>
  )
}
