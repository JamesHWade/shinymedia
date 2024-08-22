library(shiny)

ui <- fluidPage(
  input_audio_clip("one")
)

server <- function(input, output, session) {

}

shinyApp(ui, server)
