#ifndef __REPORT_H__
#define __REPORT_H__

#include <stdint.h>

struct DateTime {
  unsigned int year : 6;
  unsigned int month : 4;
  unsigned int day : 5;
  unsigned int hour : 5;                 
  unsigned int minute : 6;
  unsigned int second : 6;
} __attribute__((packed));

struct ReportItem {
  DateTime date;
  uint16_t vbat;  // in mV
  int32_t latitude,longitude; 
  uint8_t quality,satellites;
  uint16_t temperature;
  uint16_t time_to_fix;
} __attribute__((packed));

#endif
