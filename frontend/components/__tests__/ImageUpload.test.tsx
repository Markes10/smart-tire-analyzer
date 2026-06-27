import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { ImageUpload } from '../image-upload'

function createMockFile(name: string, size: number, type: string): File {
  const blob = new Blob(['x'.repeat(size)], { type })
  return new File([blob], name, { type })
}

function uploadFile(input: HTMLElement, file: File) {
  Object.defineProperty(input, 'files', { value: [file], writable: false })
  fireEvent.change(input)
}

describe('ImageUpload', () => {
  const defaultProps = {
    label: 'Tire Image',
    description: 'Upload a tire photo',
    value: null,
    onChange: vi.fn(),
  }

  it('renders with correct initial state', () => {
    render(<ImageUpload {...defaultProps} />)

    expect(screen.getByText('Tire Image')).toBeInTheDocument()
    expect(screen.getByText('Upload a tire photo')).toBeInTheDocument()
    expect(screen.getByText('Drop image here or click to upload')).toBeInTheDocument()
    expect(screen.getByText('Browse')).toBeInTheDocument()
    expect(screen.getByText('Camera')).toBeInTheDocument()
  })

  it('shows error for files > 10MB', async () => {
    const user = userEvent.setup()
    render(<ImageUpload {...defaultProps} />)

    const largeFile = createMockFile('large.jpg', 11 * 1024 * 1024, 'image/jpeg')
    const input = screen.getByLabelText('Tire Image image upload')

    await user.upload(input, largeFile)

    expect(screen.getByText('Image is too large. Please choose an image under 10MB.')).toBeInTheDocument()
  })

  it('shows error for non-image files', () => {
    render(<ImageUpload {...defaultProps} />)

    const textFile = createMockFile('test.txt', 100, 'text/plain')
    const input = screen.getByLabelText('Tire Image image upload')
    uploadFile(input, textFile)

    expect(screen.getByText('Please choose an image file.')).toBeInTheDocument()
  })

  it('shows error for unsupported image types', () => {
    render(<ImageUpload {...defaultProps} />)

    const gifFile = createMockFile('test.gif', 100, 'image/gif')
    const input = screen.getByLabelText('Tire Image image upload')
    uploadFile(input, gifFile)

    expect(screen.getByText('Please choose a JPEG, PNG, or WebP image.')).toBeInTheDocument()
  })

  it('accepts valid image files and calls onChange', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<ImageUpload {...defaultProps} onChange={onChange} />)

    const validFile = createMockFile('tire.jpg', 1024, 'image/jpeg')
    const input = screen.getByLabelText('Tire Image image upload')

    await user.upload(input, validFile)

    expect(onChange).toHaveBeenCalledWith(validFile, expect.stringContaining('data:'))
  })

  it('shows image preview when value is provided', () => {
    render(<ImageUpload {...defaultProps} value="data:image/jpeg;base64,fake" />)

    const img = screen.getByAltText('Tire Image')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', 'data:image/jpeg;base64,fake')
    expect(screen.getByText('Replace')).toBeInTheDocument()
    expect(screen.getByText('Retake')).toBeInTheDocument()
  })

  it('removes image when X button is clicked', () => {
    const onChange = vi.fn()
    render(<ImageUpload {...defaultProps} value="data:image/jpeg;base64,fake" onChange={onChange} />)

    const removeButton = screen.getByRole('button', { name: '' })
    fireEvent.click(removeButton)

    expect(onChange).toHaveBeenCalledWith(null, null)
  })

  it('does not call onChange when no file is selected', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<ImageUpload {...defaultProps} onChange={onChange} />)

    const input = screen.getByLabelText('Tire Image image upload')

    await user.upload(input, [])

    expect(onChange).not.toHaveBeenCalled()
  })
})
