# Tailwind CSS & Styling Guide

Tailwind CSS v4 with Shadcn/ui components.

## Tailwind v4 Configuration

```css
/* styles.css */
@import "tailwindcss";

@theme {
  --color-primary: oklch(0.5 0.2 240);
  --radius-lg: 0.5rem;
}
```

## Layout Patterns

### Flexbox
```tsx
<div className="flex items-center justify-between gap-4">
  <span>Left</span>
  <span>Right</span>
</div>

// Vertical centering
<div className="flex items-center justify-center min-h-screen">
  <Content />
</div>
```

### Grid
```tsx
// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => <Card key={item.id} />)}
</div>
```

### Container
```tsx
<div className="container mx-auto px-4">
  <Content />
</div>
```

## Spacing

```tsx
// Padding
<div className="p-4 px-6 py-2">

// Margin
<div className="m-4 mx-auto my-2">

// Gap (for flex/grid)
<div className="gap-4 gap-x-2 gap-y-4">
```

## Typography

```tsx
<h1 className="text-4xl font-bold tracking-tight">Heading</h1>
<p className="text-muted-foreground text-sm">Description</p>
<span className="font-medium">Label</span>
```

## Semantic Colors

```tsx
// Background
<div className="bg-background bg-primary bg-muted">

// Text
<span className="text-foreground text-primary text-muted-foreground">

// Border
<div className="border border-border border-primary">
```

## Responsive Design

```tsx
// Mobile-first breakpoints
<div className="w-full md:w-1/2 lg:w-1/3">

// Hide/show at breakpoints
<div className="hidden md:block">Desktop only</div>
<div className="block md:hidden">Mobile only</div>
```

## Interactive States

```tsx
<button className="hover:bg-primary/90 focus:ring-2 focus:ring-primary disabled:opacity-50">
  Click me
</button>

<a className="hover:underline">Link</a>
```

## Dark Mode

```tsx
// Automatic with semantic colors
<div className="bg-background text-foreground">

// Force dark
<div className="dark">
  <div className="bg-background"> {/* Uses dark theme colors */}
```

## Shadcn/ui Components

### Button
```tsx
import { Button } from "@/components/ui/button";

// Variants
<Button variant="default">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Destructive</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
<Button size="icon"><IconPlus /></Button>

// With loading
<Button disabled>
  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
  Please wait
</Button>
```

### Card
```tsx
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
  <CardFooter className="flex justify-between">
    <Button variant="outline">Cancel</Button>
    <Button>Save</Button>
  </CardFooter>
</Card>
```

### Dialog
```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

<Dialog>
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Title</DialogTitle>
      <DialogDescription>Description</DialogDescription>
    </DialogHeader>
    <div>Content</div>
    <DialogFooter>
      <Button>Save</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Form
```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const schema = z.object({
  email: z.string().email(),
});

function MyForm() {
  const form = useForm({
    resolver: zodResolver(schema),
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Submit</Button>
      </form>
    </Form>
  );
}
```

## Utility: cn() Function

```tsx
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Usage
<div className={cn(
  "flex items-center p-4",
  isActive && "bg-primary text-primary-foreground",
  className
)}>
```

## Common Patterns

### Card with Actions
```tsx
<Card>
  <CardHeader className="flex flex-row items-center justify-between">
    <CardTitle>Title</CardTitle>
    <Button variant="ghost" size="sm">Action</Button>
  </CardHeader>
  <CardContent className="space-y-4">
    Content
  </CardContent>
</Card>
```

### Loading State
```tsx
<Button disabled={isLoading}>
  {isLoading ? (
    <>
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      Loading...
    </>
  ) : (
    'Submit'
  )}
</Button>
```

### Form Layout
```tsx
<form className="space-y-4">
  <div className="space-y-2">
    <Label htmlFor="email">Email</Label>
    <Input id="email" type="email" />
  </div>
  <Button type="submit" className="w-full">
    Submit
  </Button>
</form>
```

## Anti-Patterns

```tsx
// Bad: Inline styles with Tailwind
<div style={{ marginTop: '16px' }} className="p-4">

// Good: Use Tailwind classes
<div className="mt-4 p-4">

// Bad: Overusing !important
<div className="!mt-4 !p-4">

// Good: Use proper specificity with cn()
<div className={cn("mt-4 p-4", className)}>

// Bad: Hardcoded colors
<div className="bg-[#3b82f6]">

// Good: Use semantic colors
<div className="bg-primary">
```

## CLI Commands

```bash
# Add Shadcn components
bunx --bun shadcn@latest add button card dialog form

# Initialize Shadcn
bunx --bun shadcn@latest init
```
