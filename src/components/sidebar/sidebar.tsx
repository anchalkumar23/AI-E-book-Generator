import {
  BookOpen,
  Star,
  ArrowClockwise,
  Baby,
  BookBookmark,
  Compass,
  GraduationCap,
  Gear,
  PlusCircle,
} from '@phosphor-icons/react'
import s from './sidebar.module.css'

interface Props {
  active: string
  bookCounts: { all: number; favorites: number; generating: number }
  onNavChange: (id: string) => void
  onNewBook: () => void
}

const NAV_GROUPS = [
  {
    label: 'Library',
    items: [
      { id: 'all',        Icon: BookOpen,      label: 'All Books',  countKey: 'all'        as const },
      { id: 'favorites',  Icon: Star,          label: 'Favorites',  countKey: 'favorites'  as const },
      { id: 'generating', Icon: ArrowClockwise, label: 'Generating', countKey: 'generating' as const },
    ],
  },
  {
    label: 'Types',
    items: [
      { id: 'childrens',   Icon: Baby,         label: "Children's" },
      { id: 'tutorial',    Icon: BookBookmark,  label: 'Tutorials'  },
      { id: 'guide',       Icon: Compass,       label: 'Guides'     },
      { id: 'educational', Icon: GraduationCap, label: 'Educational'},
    ],
  },
  {
    label: 'Account',
    items: [
      { id: 'settings', Icon: Gear, label: 'Settings' },
    ],
  },
]

export function Sidebar({ active, bookCounts, onNavChange, onNewBook }: Props) {
  return (
    <aside className={s.sidebar}>
      <div className={s.logo}>
        <div className={s.logoMark}>
          <BookOpen size={14} weight="bold" />
        </div>
        <span className={s.logoText}>Pageforge</span>
      </div>

      <button className={s.newBook} onClick={onNewBook}>
        <PlusCircle size={15} weight="bold" />
        New Book
      </button>

      <nav className={s.nav}>
        {NAV_GROUPS.map(({ label, items }) => (
          <div key={label}>
            <div className={s.sectionLabel}>{label}</div>
            {items.map(({ id, Icon, label: itemLabel, ...rest }) => {
              const countKey = 'countKey' in rest ? rest.countKey : undefined
              const count = countKey !== undefined ? bookCounts[countKey] : undefined
              return (
                <button
                  key={id}
                  className={`${s.navItem} ${active === id ? s.active : ''}`}
                  onClick={() => onNavChange(id)}
                >
                  <span className={s.icon}>
                    <Icon size={15} weight={active === id ? 'bold' : 'regular'} />
                  </span>
                  {itemLabel}
                  {count !== undefined && (
                    <span className={s.badge}>{count}</span>
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </nav>

    </aside>
  )
}
