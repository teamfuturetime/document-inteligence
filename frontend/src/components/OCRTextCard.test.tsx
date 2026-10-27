import{cleanup,fireEvent,render,screen,waitFor}from'@testing-library/react'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import'@testing-library/jest-dom/vitest'
import OCRTextCard from'./OCRTextCard'
import type{OCRPage}from'../types'

const pages:OCRPage[]=[{page_number:1,width:1200,height:1600,blocks:[{type:'key_value',text:'MST: 0101234567',key:'MST',value:'0101234567',confidence:.42,bbox:[10,20,300,40],needs_review:true,lines:[]}]}]

describe('OCRTextCard',()=>{
  const writeText=vi.fn().mockResolvedValue(undefined)
  beforeEach(()=>{writeText.mockClear();Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}})})
  afterEach(cleanup)

  it('mặc định hiển thị bản dễ đọc và có đủ ba chế độ',()=>{
    render(<OCRTextCard cleanedText="Nội dung dễ đọc" rawText={'NỘI  DUNG\n||||'} pages={pages}/>)
    expect(screen.getByText('Nội dung dễ đọc')).toBeInTheDocument()
    expect(screen.getByRole('tab',{name:'Văn bản dễ đọc'})).toHaveAttribute('aria-selected','true')
    expect(screen.getByRole('tab',{name:'OCR gốc'})).toBeInTheDocument()
    expect(screen.getByRole('tab',{name:'Cấu trúc tài liệu'})).toBeInTheDocument()
  })

  it('hiển thị nguyên văn raw OCR ở chế độ OCR gốc',()=>{
    const{container}=render(<OCRTextCard cleanedText="Sạch" rawText={'NỘI  DUNG\n||||'}/>)
    fireEvent.click(screen.getByRole('tab',{name:'OCR gốc'}))
    expect(container.querySelector('pre')?.textContent).toBe('NỘI  DUNG\n||||')
  })

  it('fallback về raw và hiển thị empty state',()=>{
    const{rerender}=render(<OCRTextCard cleanedText={null} rawText="Nội dung OCR gốc"/>)
    expect(screen.getByText('Nội dung OCR gốc')).toBeInTheDocument()
    rerender(<OCRTextCard cleanedText=" " rawText={null}/>)
    expect(screen.getByText('Chưa có văn bản OCR')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Sao chép'})).toBeDisabled()
  })

  it('hiển thị cấu trúc và confidence OCR thật',()=>{
    render(<OCRTextCard cleanedText="MST: 0101234567" rawText="MST: 0101234567" pages={pages}/>)
    fireEvent.click(screen.getByRole('tab',{name:'Cấu trúc tài liệu'}))
    expect(screen.getByText('Trang 1')).toBeInTheDocument()
    expect(screen.getByText('OCR 42% · cần kiểm tra')).toBeInTheDocument()
    expect(screen.getByText('0101234567')).toBeInTheDocument()
  })

  it('không tạo cấu trúc giả khi backend chưa cung cấp',()=>{
    render(<OCRTextCard cleanedText="Văn bản" rawText="Văn bản" pages={[]}/>)
    fireEvent.click(screen.getByRole('tab',{name:'Cấu trúc tài liệu'}))
    expect(screen.getByText('Chưa có dữ liệu cấu trúc')).toBeInTheDocument()
  })

  it('sao chép nội dung của chế độ đang chọn',async()=>{
    render(<OCRTextCard cleanedText="Nội dung sạch" rawText="Nội dung thô"/>)
    fireEvent.click(screen.getByRole('tab',{name:'OCR gốc'}))
    fireEvent.click(screen.getByRole('button',{name:'Sao chép'}))
    await waitFor(()=>expect(writeText).toHaveBeenCalledWith('Nội dung thô'))
    expect(screen.getByRole('button',{name:'Đã sao chép'})).toBeInTheDocument()
  })
})
