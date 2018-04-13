
#------------------------------------------------------------------------------
library(jsonlite)
library(tidyr)
library(data.table)


setwd("C:/Users/L.GonzalezMorales/Documents/GitHub/FIS4SDGs/")


#-----------------------------------------------------------------------------
# List of countreis to be plotted on a map (with XY coordinates)
#------------------------------------------- ----------------------------------

countryListXY <- as.data.frame(read.table("CountryListXY.txt", 
                                          header = TRUE, 
                                          sep = "\t",
                                          quote = "",
                                          na.strings = "", 
                                          stringsAsFactors = FALSE,
                                          encoding = "UTF-8"))

countryListXY[countryListXY$geoAreaCode==248,"geoAreaName"] <- "Åland Islands"
countryListXY[countryListXY$geoAreaCode==384,"geoAreaName"] <- "Côte d'Ivoire"
countryListXY[countryListXY$geoAreaCode==531,"geoAreaName"] <- "Curaçao"
countryListXY[countryListXY$geoAreaCode==638,"geoAreaName"] <- "Réunion"
countryListXY[countryListXY$geoAreaCode==652,"geoAreaName"] <- "Saint Barthélemy"

#------------------------------------------------------------------------------
# List of al series available 

SeriesList  <- as.data.table(fromJSON("https://unstats.un.org/SDGAPI/v1/sdg/Series/List?allreleases=false"))[,c("release","code","description")]

#------------------------------------------------------------------------------
# Pull data for each series
#------------------------------------------------------------------------------
#for(i in 1:1)
for(i in 1:length(SeriesList[[2]]))
{
    pageSize <- fromJSON(paste("https://unstats.un.org/SDGAPI/v1/sdg/Series/Data?seriesCode=",SeriesList[i][[2]],"&pageSize=2",sep=""))$totalElements
    
    queryString <- paste("https://unstats.un.org/SDGAPI/v1/sdg/Series/Data?seriesCode=",SeriesList[i][[2]],"&pageSize=",pageSize,sep="")
    
    #queryString <- paste("https://unstats.un.org/SDGAPI/v1/sdg/Series/Data?seriesCode=","AG_FPA_MILLET","&pageSize=5000",sep="")

    x <- fromJSON(queryString )

    
    # Create grid of key columns
    geoAreaCodes <- countryListXY$geoAreaCode
    
    slice <- unique(x$data$dimensions)
    slice$sliceId <- 1:nrow(slice)
    
    years <- unique(x$data$timePeriodStart)
    
    grid <- expand.grid(geoAreaCode = geoAreaCodes, 
                        sliceId = slice$sliceId, 
                        years = years)
    
    grid$series.release <- SeriesList[i][[1]]
    grid$series.code <- SeriesList[i][[2]]
    grid$series.description <- SeriesList[i][[3]]
    
    # Extract data matrix:
    data <- x$data[,c("geoAreaCode",
                      "timePeriodStart",
                      "value",
                      "valueType",
                      "time_detail",
                      "source")]
    
    colnames(data)[colnames(data)=="timePeriodStart"] <- "years"
    
    # Need to select unique records for the case of multi-indicator series:
    data <- unique(cbind(data, x$data$dimensions, x$data$attributes))
    
    data$value <- as.numeric(data$value)
    
    
    if(sum(data$geoAreaCode %in% geoAreaCodes)>0){
      
      
      # Create data cube by left-joining grid and data matrix:
      cube <- merge(merge(merge(grid,
                                countryListXY,
                                all.x = TRUE),
                          slice,
                          all.x = TRUE),
                    data,
                    all.x = TRUE)
      
      cube <- cube[order(cube$geoAreaCode, cube$sliceId, cube$years),]
      
      #-------------------------------------------
      # Generate cube pivot
      #-------------------------------------------
      
      columns <- c("series.release", "series.code","series.description","geoAreaCode","X", "Y", "ISO3CD", "geoAreaName", "sliceId",
                   names(x$data$dimensions), "years", "value")
      
      cube.pivot <- cube[,columns] 
      cube.pivot <-  cube[,columns]  %>% spread(years,value)
      
      last.year <- max(cube[,"years"])
      
      
      last.5.years <- names(cube.pivot) %in% as.character(seq(last.year-4,last.year,1))
      
      if(sum(last.5.years)>1)  {
        cube.pivot$last.5.years.mean <- apply(cube.pivot[,last.5.years],1,mean, na.rm=TRUE)
      } 
      
      
      cube <- as.data.table(cube)
      cube.latest <- cube[cube[!is.na(value), .I[years == max(years)], by =  c("geoAreaCode", "sliceId")]$V1]
      
      names(cube.latest)
      
      cube.latest <- cube.latest[,-c("OBJECTID", "valueType", "time_detail"),  with=FALSE]
      setnames(cube.latest, old = "years", new = "latest.year")
      setnames(cube.latest, old = "value", new = "latest.value")
      setnames(cube.latest, old = "source", new = "latest.source")
      if("Nature" %in% names(cube.latest))
        {
        setnames(cube.latest, old = "Nature", new = "latest.nature")  
      }
      
      
      cube.pivot <- merge(cube.pivot, cube.latest, all.x = TRUE)      
  
      write.table(cube, 
                  file = paste(SeriesList[i][[2]],"_cube.csv", sep=""), 
                   append = FALSE,
                   quote = FALSE, 
                   sep = "\t",
                   eol = "\n", 
                   na = "", 
                   dec = ".", 
                   row.names = FALSE,
                   col.names = TRUE, 
                   fileEncoding = "UTF-8")
      
      
      write.table(cube.pivot, 
                  file = paste(SeriesList[i][[2]],"_cube.pivot.csv", sep=""), 
                  append = FALSE,
                  quote = FALSE, 
                  sep = "\t",
                  eol = "\n", 
                  na = "", 
                  dec = ".", 
                  row.names = FALSE,
                  col.names = TRUE, 
                  fileEncoding = "UTF-8")
      
    }

}
