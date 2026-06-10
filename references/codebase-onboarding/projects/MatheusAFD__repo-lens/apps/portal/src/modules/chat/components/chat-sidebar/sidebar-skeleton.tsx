import { Skeleton } from '@repo/ui/components/skeleton'

export function SidebarSkeleton() {
  return (
    <div className="flex flex-col gap-1 px-1">
      {[1, 2, 3, 4].map((key) => (
        <Skeleton key={key} className="h-9 w-full rounded-md" />
      ))}
    </div>
  )
}
