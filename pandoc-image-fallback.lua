local function exists(path)
  local f = io.open(path, "rb")
  if f then
    f:close()
    return true
  end
  return false
end

function Image(img)
  local src = img.src
  local base = src:match("^(.*)%.pdf$")
  if not base then
    return img
  end

  local generated_png = ".docx-build/pdf-images/" .. base .. ".png"
  local png = base .. ".png"
  local svg = base .. ".svg"

  if exists(generated_png) then
    img.src = generated_png
  elseif exists(png) then
    img.src = png
  elseif exists(svg) then
    img.src = svg
  end

  return img
end

function Math(math)
  local text = math.text
  text = text:gsub("\\begin%s*{%s*equation%*?%s*}", "")
  text = text:gsub("\\end%s*{%s*equation%*?%s*}", "")
  text = text:gsub("\\label%s*{%s*[^}]+%s*}", "")
  text = text:gsub("^%s+", ""):gsub("%s+$", "")
  math.text = text
  return math
end
