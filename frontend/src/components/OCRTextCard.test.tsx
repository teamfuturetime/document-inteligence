import{cleanup,fireEvent,render,screen,waitFor}from'@testing-library/react'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import'@testing-library/jest-dom/vitest'
import OCRTextCard from'./OCRTextCard'

describe('OCRTextCard',()=>{
  const writeText=vi.fn().mockResolvedValue(undefined)

  beforeEach(()=>{
    writeText.mockClear()
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}})
  })
  afterEach(cleanup)

  it('ưu tiên bản OCR đã làm sạch và giữ bản thô trong mục kỹ thuật',()=>{
    const{container}=render(<OCRTextCard cleanedText="Nội dung dễ đọc" rawText={'NỘI  DUNG\n||||'}/>)

    expect(screen.getByText('Nội dung dễ đọc')).toBeInTheDocument()
    expect(screen.getByText('Văn bản OCR thô (dành cho kỹ thuật)')).toBeInTheDocument()
    expect(container.querySelector('pre')?.textContent).toBe('NỘI  DUNG\n||||')
  })

  it('dùng bản thô khi chưa có bản làm sạch',()=>{
    render(<OCRTextCard cleanedText={null} rawText="Nội dung OCR gốc"/>)
    expect(screen.getAllByText('Nội dung OCR gốc')).toHaveLength(2)
  })

  it('hiển thị hướng dẫn khi OCR rỗng',()=>{
    render(<OCRTextCard cleanedText=" " rawText={null}/>)
    expect(screen.getByText('Chưa có văn bản OCR')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Sao chép'})).toBeDisabled()
  })

  it('sao chép nội dung đang đọc',async()=>{
    render(<OCRTextCard cleanedText="Nội dung sạch" rawText="Nội dung thô"/>)
    fireEvent.click(screen.getByRole('button',{name:'Sao chép'}))

    await waitFor(()=>expect(writeText).toHaveBeenCalledWith('Nội dung sạch'))
    expect(screen.getByRole('button',{name:'Đã sao chép'})).toBeInTheDocument()
  })
})
