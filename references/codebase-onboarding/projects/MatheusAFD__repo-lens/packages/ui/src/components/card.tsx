import { cn } from '@/lib/utils'
import type { ComponentProps } from 'react'

interface CardProps extends ComponentProps<'div'> {}

export function Card(props: CardProps) {
  const { className, ...rest } = props
  return (
    <div
      className={cn('rounded-xl border bg-card text-card-foreground shadow', className)}
      {...rest}
    />
  )
}

interface CardHeaderProps extends ComponentProps<'div'> {}

export function CardHeader(props: CardHeaderProps) {
  const { className, ...rest } = props
  return <div className={cn('flex flex-col gap-1.5 p-6', className)} {...rest} />
}

interface CardTitleProps extends ComponentProps<'h3'> {}

export function CardTitle(props: CardTitleProps) {
  const { className, ...rest } = props
  return <h3 className={cn('font-semibold leading-none tracking-tight', className)} {...rest} />
}

interface CardDescriptionProps extends ComponentProps<'p'> {}

export function CardDescription(props: CardDescriptionProps) {
  const { className, ...rest } = props
  return <p className={cn('text-sm text-muted-foreground', className)} {...rest} />
}

interface CardContentProps extends ComponentProps<'div'> {}

export function CardContent(props: CardContentProps) {
  const { className, ...rest } = props
  return <div className={cn('p-6 pt-0', className)} {...rest} />
}

interface CardFooterProps extends ComponentProps<'div'> {}

export function CardFooter(props: CardFooterProps) {
  const { className, ...rest } = props
  return <div className={cn('flex items-center p-6 pt-0', className)} {...rest} />
}
