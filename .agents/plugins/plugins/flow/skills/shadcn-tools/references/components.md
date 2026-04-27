# ShadCN Core Components

## Button

```tsx
import { Button } from "@/components/ui/button"

// Variants
<Button variant="default">Primary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>

// As child (render as different element)
<Button asChild>
  <Link to="/dashboard">Go to Dashboard</Link>
</Button>
```

## Input & Label

```tsx
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input id="email" type="email" placeholder="name@example.com" />
</div>
```

## Card

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

<Card>
  <CardHeader><CardTitle>Card Title</CardTitle></CardHeader>
  <CardContent><p>Content goes here</p></CardContent>
</Card>
```

## Select

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

<Select>
  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
  <SelectContent>
    <SelectItem value="1">Option 1</SelectItem>
  </SelectContent>
</Select>
```

---

## Utilities

### cn() Function

Merges Tailwind classes intelligently.

```tsx
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```
