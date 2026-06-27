import { z } from 'zod'

export const emailSchema = z.string().email('Invalid email address')
export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one digit')

export const signupSchema = z.object({
  firstName: z.string().min(1, 'First name is required').max(50),
  lastName: z.string().min(1, 'Last name is required').max(50),
  email: emailSchema,
  password: passwordSchema,
  geminiKey: z.string().optional(),
  mapillaryToken: z.string().optional(),
  openweatherKey: z.string().optional(),
})

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
})

export const contactSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  email: emailSchema,
  subject: z.string().min(1, 'Subject is required'),
  message: z.string().min(10, 'Message must be at least 10 characters').max(2000),
})

export const feedbackSchema = z.object({
  sessionId: z.string().uuid('Invalid session ID'),
  treadDepth1: z.number().min(0).max(12, 'Tread depth must be 0-12mm').optional(),
  treadDepth2: z.number().min(0).max(12, 'Tread depth must be 0-12mm').optional(),
  treadDepth3: z.number().min(0).max(12, 'Tread depth must be 0-12mm').optional(),
  treadDepth4: z.number().min(0).max(12, 'Tread depth must be 0-12mm').optional(),
  wearPattern: z.string().optional(),
  feedbackType: z.enum(['correct', 'wrong', 'inaccurate']),
  comment: z.string().max(1000).optional(),
})

export const enterpriseSalesSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  email: emailSchema,
  phone: z.string().regex(/^[\d\s\-+()]{7,20}$/, 'Invalid phone number').optional(),
  company: z.string().min(1, 'Company is required').max(200),
  role: z.string().min(1, 'Role is required').max(100),
  fleetSize: z.string().optional(),
  needs: z.string().min(10, 'Please describe your needs').max(2000),
  timeline: z.string().optional(),
})

export const supportTicketSchema = z.object({
  category: z.string().min(1, 'Category is required'),
  email: emailSchema,
  priority: z.enum(['low', 'medium', 'high', 'urgent']),
  subject: z.string().min(5, 'Subject must be at least 5 characters').max(200),
  description: z.string().min(20, 'Please provide more detail').max(5000),
  environment: z.string().optional(),
})

export type SignupInput = z.infer<typeof signupSchema>
export type LoginInput = z.infer<typeof loginSchema>
export type ContactInput = z.infer<typeof contactSchema>
export type FeedbackInput = z.infer<typeof feedbackSchema>
export type EnterpriseSalesInput = z.infer<typeof enterpriseSalesSchema>
export type SupportTicketInput = z.infer<typeof supportTicketSchema>
