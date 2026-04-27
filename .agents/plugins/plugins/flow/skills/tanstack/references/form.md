# TanStack Form

## Basic Form

```tsx
import { useForm } from '@tanstack/react-form'

function ContactForm() {
  const form = useForm({
    defaultValues: { name: '' },
    onSubmit: async ({ value }) => {
      await api.submitContact(value)
    },
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); form.handleSubmit() }}>
      <form.Field
        name="name"
        children={(field) => (
          <div>
            <Label htmlFor={field.name}>Name</Label>
            <Input id={field.name} value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} />
          </div>
        )}
      />
      <Button type="submit">Submit</Button>
    </form>
  )
}
```

## With Zod Validation

```tsx
import { zodValidator } from '@tanstack/zod-form-adapter'
import { z } from 'zod'

const userSchema = z.object({
  email: z.string().email('Invalid email'),
})

// Inside component
const form = useForm({
  defaultValues: { email: '' },
  validatorAdapter: zodValidator(),
  validators: { onChange: userSchema },
})
```
